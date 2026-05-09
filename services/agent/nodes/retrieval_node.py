"""
RetrievalNode — 并行获取天气/路线（主路径）+ 3 个独立策略 ReAct 循环（策略路径）。

主路径（并行）：
  - 天气查询    — mock，预留真实 API
  - 路线信息    — 从 routes.json 读取静态路线（origin + static_routes）
  结果写入 state.retrieval（activities/restaurants 为空列表，仅 weather/route_info 有效）

策略路径（3 个独立 LLM ReAct 循环，并行）：
  每个循环持有完全隔离的 LLM 对话上下文：
    1. LLM 根据 style_hint 和 intent 生成搜索关键词（循环外调用一次）
    2. 用生成的关键词搜索 AMap（activity + restaurant）
    3. 把所有候选 POI 的关键字段序列化后喂给 LLM，由 LLM 判断是否满意；
       LLM 返回 satisfied=true 时退出，否则给出新关键词继续搜，最多 3 轮
  结果写入 state.retrieval_strategies，PlanningNode 优先使用这些候选集

state.retrieval 仅作为三策略全挂时的 fallback 和 weather/route_info 来源。

注意：各 POI 的出行时间（travel_minutes）直接存储在 POISchema 对象上，
PlanningNode 序列化 POI 列表时直接读取，不依赖 route_info 中的任何映射。
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.repositories.mock_poi_repository import MockPOIRepository
from app.schemas.planning import POISchema, UserIntentSchema
from app.services.activity_workflow import _is_open_for_window
from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, RetrievalResult, TraceEvent
from llm.base import LLMClient, LLMMessage
from llm.structured_output import parse_json_response, LLMParseError
from tools.poi.base import AbstractPOISearcher

logger = logging.getLogger(__name__)

# 默认关键词（LLM 解析失败时使用）
_DEFAULT_ACTIVITY_KEYWORDS = "景点|公园|休闲"
_DEFAULT_RESTAURANT_KEYWORDS = "餐厅"


# ---------------------------------------------------------------------------
# RetrievalNode
# ---------------------------------------------------------------------------

class RetrievalNode(BaseNode):
    """主路径 + 策略路径并行检索节点，结果写入 state.retrieval / state.retrieval_strategies。

    主路径（并行）：
      - 天气查询    — mock，预留真实 API
      - 路线信息    — 从 routes.json 读取静态路线（origin + static_routes）

    策略路径（3 个独立 LLM ReAct 循环，并行）：
      每个循环拥有完全隔离的 LLM 对话上下文：
        1. LLM 根据 style_hint 和 intent 生成搜索关键词（循环外调用一次）
        2. 用生成的关键词搜索 AMap（activity + restaurant）
        3. 把所有候选 POI 的关键字段序列化后喂给 LLM，由 LLM 判断是否满意；
         LLM 返回 satisfied=true 时退出，否则给出新关键词继续搜，最多 3 轮
      结果写入 state.retrieval_strategies，PlanningNode 优先使用这些候选集。

    state.retrieval 仅作为三策略全挂时的 fallback 和 weather/route_info 来源。

    依赖注入：
      searcher    — AbstractPOISearcher（MockPOISearcher 或 AmapSearcher）
      llm_client  — LLMClient（用于策略 ReAct 循环中动态生成关键词）
      routes_path — routes.json 文件路径；None 时自动从项目根目录推断
    """

    def __init__(
        self,
        searcher: AbstractPOISearcher,
        llm_client: LLMClient | None = None,
        repository: MockPOIRepository | None = None,
        routes_path: Path | None = None,
    ) -> None:
        self._searcher = searcher
        self._llm_client = llm_client
        # repository 参数保留以维持向后兼容的构造函数签名，当前实现未使用
        self._routes_path = routes_path or self._default_routes_path()

    # ------------------------------------------------------------------
    # 内部辅助：POI 列表序列化为可读文本（供 Observe 步骤使用）
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_candidates(
        activities: list[POISchema],
        restaurants: list[POISchema],
    ) -> str:
        """将活动和餐厅候选列表序列化为简洁可读的文本，供 LLM Observe 步骤使用。

        序列化字段：名称、类别、评分、距离（km）、营业时间、推荐游玩时长（min）。
        """
        lines: list[str] = []

        if activities:
            lines.append(f"【活动候选 {len(activities)} 条】")
            for i, poi in enumerate(activities, 1):
                lines.append(
                    f"  {i}. {poi.name}（{poi.subcategory}）"
                    f" | 评分 {poi.rating}/5"
                    f" | 距离 {poi.distance_km:.1f}km"
                    f" | 营业 {poi.business_hours.open}–{poi.business_hours.close}"
                    f" | 推荐游玩 {poi.recommended_duration_minutes}min"
                )
        else:
            lines.append("【活动候选 0 条】")

        if restaurants:
            lines.append(f"【餐厅候选 {len(restaurants)} 条】")
            for i, poi in enumerate(restaurants, 1):
                lines.append(
                    f"  {i}. {poi.name}（{poi.subcategory}）"
                    f" | 评分 {poi.rating}/5"
                    f" | 距离 {poi.distance_km:.1f}km"
                    f" | 营业 {poi.business_hours.open}–{poi.business_hours.close}"
                    f" | 推荐游玩 {poi.recommended_duration_minutes}min"
                )
        else:
            lines.append("【餐厅候选 0 条】")

        return "\n".join(lines)

    @staticmethod
    def _default_routes_path() -> Path:
        # services/agent/nodes/retrieval_node.py → 上 3 级到项目根
        return Path(__file__).resolve().parents[3] / "data" / "mock" / "routes.json"

    # ------------------------------------------------------------------
    # BaseNode.run
    # ------------------------------------------------------------------

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="开始检索：天气、路线（并行）+ 3 个策略 ReAct 循环（并行）...",
        ))

        intent = state.intent
        if intent is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message="state.intent 为空，无法执行检索",
            ))
            logger.error("[%s] state.intent is None, skipping retrieval", self.name)
            return state

        # 主路径：只保留天气和路线（POI 搜索完全交给策略路径）
        weather, route_info = await asyncio.gather(
            asyncio.create_task(self._fetch_weather(intent)),
            asyncio.create_task(self._fetch_routes(intent)),
        )

        state.retrieval = RetrievalResult(
            activities=[],
            restaurants=[],
            weather=weather,
            route_info=route_info,
        )

        # 策略路径：3 个独立 ReAct 循环并行，各自用 LLM 生成关键词并搜索
        scenario = intent.scenario if intent.scenario else ""
        style_hints = await self._generate_style_hints(intent, scenario)

        strategy_tasks = [
            asyncio.create_task(
                self._run_strategy_react_loop(intent, hint)
            )
            for hint in style_hints
        ]
        strategy_results_raw = await asyncio.gather(*strategy_tasks, return_exceptions=True)

        # 过滤掉异常，保留 RetrievalResult
        state.retrieval_strategies = [
            r for r in strategy_results_raw if isinstance(r, RetrievalResult)
        ]

        total_activities = sum(len(r.activities) for r in state.retrieval_strategies)
        total_restaurants = sum(len(r.restaurants) for r in state.retrieval_strategies)

        logger.info(
            "[%s] retrieval done: %d strategies, total activities=%d, total restaurants=%d",
            self.name,
            len(state.retrieval_strategies),
            total_activities,
            total_restaurants,
        )

        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=(
                f"检索完成：{len(state.retrieval_strategies)} 个策略候选集，"
                f"共 {total_activities} 个活动、{total_restaurants} 个餐厅，"
                f"天气：{weather}"
            ),
        ))
        return state

    # ------------------------------------------------------------------
    # 策略方向生成
    # ------------------------------------------------------------------

    async def _generate_style_hints(
        self,
        intent: UserIntentSchema,
        scenario: str,
    ) -> list[str]:
        """调用 LLM 根据用户原始输入动态生成 3 个策略搜索方向。

        Args:
            intent:   用户规划意图（含 raw_text 等原始输入字段）。
            scenario: 场景标识，如 "friends_4_mixed_gender"、"family_weight_loss_child5"。

        Returns:
            list[str] — 3 个短中文策略方向（2-4 字），如 ["亲子户外", "文化艺术", "休闲社交"]。
        """
        # LLM 不可用时直接降级
        if self._llm_client is None:
            return self._fallback_style_hints(scenario)

        loop = asyncio.get_running_loop()
        raw_text = getattr(intent, "raw_text", "")

        system_content = (
            "你是一个活动规划策略设计师。请根据用户的出行意图，"
            "生成 3 个不同的搜索方向（style hints），每个方向用 2-4 个中文字概括。\n"
            "要求：\n"
            "1. 三个方向必须覆盖用户意图的不同侧面（如户外、文艺、美食、娱乐等）\n"
            "2. 每个方向用 2-4 个中文字，简洁有力\n"
            "3. 方向之间要有明显区分度，避免重叠\n"
            '以 JSON 格式返回：{"hints": ["方向1", "方向2", "方向3"]}\n'
            "不要包含任何其他内容。"
        )
        user_content = (
            f"用户原始输入：{raw_text}\n"
            f"场景：{scenario}\n"
            f"城市：{getattr(intent, 'city', '未知')}\n"
            f"参与者：{getattr(intent, 'participants', '未知')}\n"
            f"偏好：{getattr(intent, 'soft_preferences', [])}\n"
            "请生成 3 个不同的搜索方向。"
        )

        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ]

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._llm_client.chat(messages, json_mode=True),  # type: ignore[union-attr]
            )
            parsed = parse_json_response(response, required_fields=["hints"])
            hints: list[str] = parsed["hints"]

            if not isinstance(hints, list) or len(hints) != 3:
                logger.warning(
                    "[%s] _generate_style_hints: LLM returned %d hints (expected 3), using fallback",
                    self.name, len(hints) if isinstance(hints, list) else 0,
                )
                return self._fallback_style_hints(scenario)

            logger.debug(
                "[%s] _generate_style_hints: %s",
                self.name, hints,
            )
            return hints

        except (LLMParseError, Exception) as exc:
            logger.warning(
                "[%s] _generate_style_hints: LLM call/parse failed: %s, using fallback",
                self.name, exc,
            )
            return self._fallback_style_hints(scenario)

    @staticmethod
    def _fallback_style_hints(scenario: str) -> list[str]:
        """静态降级：生成硬编码风格 hints。"""
        if scenario == "friends_4_mixed_gender":
            return ["户外打卡", "娱乐社交", "文艺探索"]
        return ["亲子户外", "文化艺术", "休闲社交"]

    # ------------------------------------------------------------------
    # 策略 ReAct 循环
    # ------------------------------------------------------------------

    async def _run_strategy_react_loop(
        self,
        intent: UserIntentSchema,
        style_hint: str,
        max_iterations: int = 3,
    ) -> RetrievalResult:
        """单个策略的 ReAct 循环，拥有完全独立的 LLM 对话上下文。

        流程：
          1. 初始化 messages（system + user），请 LLM 生成搜索关键词
          2. 调用 LLM，解析返回的关键词 JSON
          3. 用关键词搜索活动和餐厅候选
          4. 把全部候选 POI 的关键字段序列化后追加到 messages，请 LLM 判断是否满意
          5. LLM 返回 satisfied=true → 退出；返回新关键词 → 继续迭代；达到上限 → 退出
          6. 对最终结果做营业时间过滤，返回 RetrievalResult

        LLM 是唯一的质量仲裁者：代码不再依据数量硬性判断是否充足，
        而是把完整候选列表喂给 LLM，由 LLM 判断"结果够不够、风格对不对"。

        Args:
            intent:         用户规划意图，包含城市、场景、时间窗口、人数等。
            style_hint:     本策略方向描述，如"亲子户外"、"文化艺术"、"休闲社交"。
            max_iterations: 最大迭代次数，默认 3。

        Returns:
            RetrievalResult，style 字段设为 style_hint。
        """
        loop = asyncio.get_running_loop()

        # ------ 初始化独立对话上下文 ------
        system_content = (
            f"你是一个 POI 搜索策略规划器，负责「{style_hint}」风格方向。\n"
            "你的任务是根据用户意图生成合适的高德地图搜索关键词，帮助找到最符合该风格的活动和餐厅候选。\n"
            "每次生成关键词时，以 JSON 格式返回，字段说明：\n"
            '  "activity_keywords"      — 活动搜索关键词（用 | 分隔多个词，如"公园|亲子乐园"）\n'
            '  "restaurant_keywords"    — 餐厅搜索关键词（如"亲子友好|健康轻食"）\n'
            "每轮搜索结束后，你会收到所有候选 POI 的详情列表（名称、类别、评分、距离、营业时间、推荐游玩时长）。\n"
            f"请仔细阅读候选列表，综合判断：这批候选的数量和质量是否足以支撑「{style_hint}」风格的完整行程规划？\n"
            "判断要点：候选数量是否充足、评分和品类是否符合该风格、是否有足够选择余地。\n"
            "如果满意，返回：{\"satisfied\": true}\n"
            "如果不满意（数量不足、评分偏低、风格不符等），返回新的关键词 JSON（同上格式）并说明调整原因。\n"
            "不要包含任何其他内容，直接返回纯 JSON。"
        )

        # 序列化 intent 的关键字段
        participants_desc = ""
        if hasattr(intent, "participants") and intent.participants:
            participants_desc = f"，参与者：{intent.participants}"
        diet_desc = ""
        if hasattr(intent, "diet_requirements") and intent.diet_requirements:
            diet_desc = f"，饮食要求：{intent.diet_requirements}"

        user_content = (
            f"请为「{style_hint}」风格生成搜索关键词。\n"
            f"城市：{getattr(intent, 'city', '未知')}\n"
            f"场景：{getattr(intent, 'scenario', '未知')}{participants_desc}\n"
            f"时间窗口：{getattr(intent, 'time_window', '未知')}{diet_desc}\n"
            "请生成适合该风格的活动和餐厅搜索关键词。"
        )

        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ]

        # 当前关键词（使用默认值初始化，LLM 解析失败时保底）
        activity_keywords = _DEFAULT_ACTIVITY_KEYWORDS
        restaurant_keywords = _DEFAULT_RESTAURANT_KEYWORDS

        activities: list[POISchema] = []
        restaurants: list[POISchema] = []
        # 累积变量：跨轮次去重累积搜索到的全部 POI
        all_activities: list[POISchema] = []
        all_restaurants: list[POISchema] = []
        seen_activity_ids: set[str] = set()
        seen_restaurant_ids: set[str] = set()

        # ------ 初始化（循环外）：调用 LLM 生成初始关键词 ------
        # 只在循环外调用一次，避免循环头重复调用导致"未搜索就 satisfied"的问题。
        if self._llm_client is not None:
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self._llm_client.chat(messages, json_mode=True),  # type: ignore[union-attr]
                )
                parsed = parse_json_response(response, required_fields=[])

                if "activity_keywords" in parsed:
                    activity_keywords = str(parsed["activity_keywords"])
                if "restaurant_keywords" in parsed:
                    restaurant_keywords = str(parsed["restaurant_keywords"])

                # 将初始 LLM 响应追加到 messages（维护对话上下文）
                messages.append(LLMMessage(role="assistant", content=response.content))

            except LLMParseError as exc:
                logger.warning(
                    "[%s] strategy=%r init: LLM parse error: %s，使用默认关键词",
                    self.name, style_hint, exc,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] strategy=%r init: LLM call error: %s，使用默认关键词",
                    self.name, style_hint, exc,
                )

        # 是否需要搜索餐厅（intent.include_meal=False 时跳过）
        search_restaurants = getattr(intent, "include_meal", True)

        for iteration in range(max_iterations):
            # ------ Act：使用当前关键词搜索 ------
            try:
                kw_act = activity_keywords
                kw_rest = restaurant_keywords if search_restaurants else ""
                activities, restaurants_raw = await loop.run_in_executor(
                    None,
                    lambda: self._searcher.search_with_strategy(
                        intent,
                        kw_act,
                        "",       # activity_types — 被搜索器忽略，使用硬编码白名单
                        kw_rest,
                        "050000",  # restaurant_types — 固定为餐饮服务
                    ),
                )
                # include_meal=False 时强制清空餐厅结果（即使搜索器返回了也丢弃）
                restaurants = restaurants_raw if search_restaurants else []
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] strategy=%r iteration=%d: search_with_strategy failed: %s，降级为空列表",
                    self.name, style_hint, iteration, exc,
                )
                activities, restaurants = [], []

            logger.debug(
                "[%s] strategy=%r iteration=%d: %d activities, %d restaurants",
                self.name, style_hint, iteration, len(activities), len(restaurants),
            )

            # ------ 累积：去重后追加到累积列表 ------
            new_activities = []
            new_restaurants = []
            for poi in activities:
                if poi.id not in seen_activity_ids:
                    seen_activity_ids.add(poi.id)
                    all_activities.append(poi)
                    new_activities.append(poi)
            for poi in restaurants:
                if poi.id not in seen_restaurant_ids:
                    seen_restaurant_ids.add(poi.id)
                    all_restaurants.append(poi)
                    new_restaurants.append(poi)

            # ------ Observe：展示本轮新增 POI，并告知 LLM 累计总数 ------
            candidates_text = self._serialize_candidates(new_activities, new_restaurants)
            observation = (
                f"本轮搜索新增 {len(new_activities)} 个活动、{len(new_restaurants)} 个餐厅"
                f"（累计共 {len(all_activities)} 个活动、{len(all_restaurants)} 个餐厅）：\n"
                f"{candidates_text}\n\n"
                f"请仔细阅读以上候选列表，判断它们是否数量充足、质量达标、风格符合「{style_hint}」方向。"
                "满意则返回 {\"satisfied\": true}，"
                "否则返回新的关键词 JSON 并说明调整原因。"
            )
            messages.append(LLMMessage(role="user", content=observation))

            # 最后一次迭代，不再调用 LLM，直接退出（兜底）
            if iteration == max_iterations - 1:
                break

            # ------ Think：调用 LLM 决策，获取新关键词或确认满意 ------
            if self._llm_client is None:
                # 无 LLM 客户端，单次搜索后直接退出
                break

            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self._llm_client.chat(messages, json_mode=True),  # type: ignore[union-attr]
                )
                parsed = parse_json_response(response, required_fields=[])

                messages.append(LLMMessage(role="assistant", content=response.content))

                if parsed.get("satisfied") is True:
                    logger.debug(
                        "[%s] strategy=%r: LLM satisfied at iteration %d",
                        self.name, style_hint, iteration,
                    )
                    break

                # LLM 给出了新关键词，更新并继续下一轮搜索
                if "activity_keywords" in parsed:
                    activity_keywords = str(parsed["activity_keywords"])
                if "restaurant_keywords" in parsed:
                    restaurant_keywords = str(parsed["restaurant_keywords"])

            except LLMParseError as exc:
                logger.warning(
                    "[%s] strategy=%r iteration=%d: LLM parse error: %s，退出循环",
                    self.name, style_hint, iteration, exc,
                )
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] strategy=%r iteration=%d: LLM call error: %s，退出循环",
                    self.name, style_hint, iteration, exc,
                )
                break

        # ------ Step 5: 营业时间过滤（对累积的全部 POI 做过滤）------
        open_activities, open_restaurants, rejected = await self._check_business_hours(
            intent, all_activities, all_restaurants
        )

        logger.debug(
            "[%s] strategy=%r final: %d activities, %d restaurants, %d rejected",
            self.name, style_hint, len(open_activities), len(open_restaurants), len(rejected),
        )

        return RetrievalResult(
            activities=open_activities,
            restaurants=open_restaurants,
            style=style_hint,
        )

    # ------------------------------------------------------------------
    # 天气查询（mock）
    # ------------------------------------------------------------------

    async def _fetch_weather(self, intent: UserIntentSchema) -> str:  # noqa: ARG002
        """返回固定 mock 天气字符串。

        TODO: 接入真实天气 API 时，将此方法替换为：
            response = await weather_client.get(city=intent.city, date=intent.time_window.date)
            return response.summary
        """
        return "晴，22°C，适合户外活动"

    # ------------------------------------------------------------------
    # 子任务 4：路线距离
    # ------------------------------------------------------------------

    async def _fetch_routes(self, intent: UserIntentSchema) -> dict[str, Any]:
        """从 routes.json 读取静态路线信息。

        routes.json 文件读取为同步 IO，通过 run_in_executor 放入线程池执行，
        避免阻塞 event loop。

        返回格式：
        {
          "origin": "...",
          "static_routes": [...],   # routes.json 原始条目
        }

        注意：此处不再构建 poi_id → travel_minutes 映射。各 POI 的出行时间
        直接存储在 POISchema.travel_minutes 字段上，PlanningNode 在序列化 POI
        列表时直接读取该字段，无需通过 route_info 中转。
        """
        loop = asyncio.get_running_loop()
        routes_path = self._routes_path

        def _load_routes() -> list[dict[str, Any]]:
            try:
                with routes_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except FileNotFoundError:
                logger.warning("[%s] routes.json not found at %s", self.name, routes_path)
                return []
            except json.JSONDecodeError as exc:
                logger.warning("[%s] routes.json parse error: %s", self.name, exc)
                return []

        static_routes = await loop.run_in_executor(None, _load_routes)

        return {
            "origin": intent.origin,
            "static_routes": static_routes,
        }

    # ------------------------------------------------------------------
    # 子任务 5：营业时间 / 库存检查
    # ------------------------------------------------------------------

    async def _check_business_hours(
        self,
        intent: UserIntentSchema,
        activities: list[POISchema],
        restaurants: list[POISchema],
    ) -> tuple[list[POISchema], list[POISchema], list[dict[str, Any]]]:
        """检查候选 POI 是否覆盖用户时间窗口，不营业的移入 rejected 列表。

        此方法仅做内存计算，无 IO，不需要 run_in_executor。

        Returns:
            (open_activities, open_restaurants, rejected_records)
        """
        open_activities: list[POISchema] = []
        open_restaurants: list[POISchema] = []
        rejected: list[dict[str, Any]] = []

        for poi in activities:
            if _is_open_for_window(poi, intent):
                open_activities.append(poi)
            else:
                rejected.append({
                    "poi_id": poi.id,
                    "name": poi.name,
                    "reason": "outside_business_hours",
                    "business_hours": {"open": poi.business_hours.open, "close": poi.business_hours.close},
                    "time_window": {"start": intent.time_window.start, "end": intent.time_window.end},
                })

        for poi in restaurants:
            if _is_open_for_window(poi, intent):
                open_restaurants.append(poi)
            else:
                rejected.append({
                    "poi_id": poi.id,
                    "name": poi.name,
                    "reason": "outside_business_hours",
                    "business_hours": {"open": poi.business_hours.open, "close": poi.business_hours.close},
                    "time_window": {"start": intent.time_window.start, "end": intent.time_window.end},
                })

        return open_activities, open_restaurants, rejected
