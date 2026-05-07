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
    3. 观察候选数量，充足则退出；不足则调用 LLM 调整关键词，最多 3 轮
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

# 策略关键词不足时的默认阈值
_MIN_ACTIVITIES = 3
_MIN_RESTAURANTS = 2

# 默认关键词（LLM 解析失败时使用）
_DEFAULT_ACTIVITY_KEYWORDS = "景点|公园|休闲"
_DEFAULT_ACTIVITY_TYPES = "110000|080000"
_DEFAULT_RESTAURANT_KEYWORDS = "餐厅"
_DEFAULT_RESTAURANT_TYPES = "050000"


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
        3. 观察候选数量，充足则退出；不足则 LLM 调整关键词，最多 3 轮
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
        if scenario == "friends_4_mixed_gender":
            style_hints = ["户外打卡", "娱乐社交", "文艺探索"]
        else:
            style_hints = ["亲子户外", "文化艺术", "休闲社交"]

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
          3. 并行搜索活动和餐厅候选
          4. 将观察结果追加到 messages，请 LLM 判断是否满意
          5. 若满意或达到上限 → 退出；否则用 LLM 返回的新关键词继续迭代
          6. 对最终结果做营业时间过滤，返回 RetrievalResult

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
            '  "activity_keywords"  — 活动搜索关键词（用 | 分隔多个词，如"公园|亲子乐园"）\n'
            '  "activity_types"     — 高德 POI 类型代码（用 | 分隔，如"110000|080000"）\n'
            '  "restaurant_keywords"— 餐厅搜索关键词（如"亲子友好|健康轻食"）\n'
            '  "restaurant_types"   — 餐厅 POI 类型代码（通常为"050000"）\n'
            "当你对搜索结果满意时，返回：{\"satisfied\": true}\n"
            "当你需要调整关键词时，返回新的关键词 JSON（同上格式）。\n"
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
        activity_types = _DEFAULT_ACTIVITY_TYPES
        restaurant_keywords = _DEFAULT_RESTAURANT_KEYWORDS
        restaurant_types = _DEFAULT_RESTAURANT_TYPES

        activities: list[POISchema] = []
        restaurants: list[POISchema] = []

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
                if "activity_types" in parsed:
                    activity_types = str(parsed["activity_types"])
                if "restaurant_keywords" in parsed:
                    restaurant_keywords = str(parsed["restaurant_keywords"])
                if "restaurant_types" in parsed:
                    restaurant_types = str(parsed["restaurant_types"])

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

        for iteration in range(max_iterations):
            # ------ Act：使用当前关键词搜索 ------
            try:
                kw_act = activity_keywords
                ty_act = activity_types
                kw_rest = restaurant_keywords
                ty_rest = restaurant_types
                activities, restaurants = await loop.run_in_executor(
                    None,
                    lambda: self._searcher.search_with_strategy(
                        intent,
                        kw_act,
                        ty_act,
                        kw_rest,
                        ty_rest,
                    ),
                )
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

            # ------ Observe：构造观察消息，追加到 messages ------
            observation = (
                f"搜索结果：活动候选 {len(activities)} 条，餐厅候选 {len(restaurants)} 条。\n"
            )
            sufficient = (
                len(activities) >= _MIN_ACTIVITIES and len(restaurants) >= _MIN_RESTAURANTS
            )
            if sufficient:
                observation += "候选数量充足。"
            else:
                shortage_parts: list[str] = []
                if len(activities) < _MIN_ACTIVITIES:
                    shortage_parts.append(f"活动不足（需至少 {_MIN_ACTIVITIES} 条）")
                if len(restaurants) < _MIN_RESTAURANTS:
                    shortage_parts.append(f"餐厅不足（需至少 {_MIN_RESTAURANTS} 条）")
                observation += (
                    f"{'、'.join(shortage_parts)}，请调整关键词重新搜索"
                    f"（返回新的关键词 JSON）。"
                )

            messages.append(LLMMessage(role="user", content=observation))

            # 候选已充足，直接退出，无需再问 LLM（避免 LLM 否定充足结果）
            if sufficient:
                logger.debug(
                    "[%s] strategy=%r: candidates sufficient at iteration %d, break",
                    self.name, style_hint, iteration,
                )
                break

            # 最后一次迭代，不再调用 LLM，直接退出
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
                if "activity_types" in parsed:
                    activity_types = str(parsed["activity_types"])
                if "restaurant_keywords" in parsed:
                    restaurant_keywords = str(parsed["restaurant_keywords"])
                if "restaurant_types" in parsed:
                    restaurant_types = str(parsed["restaurant_types"])

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

        # ------ Step 5: 营业时间过滤 ------
        open_activities, open_restaurants, rejected = await self._check_business_hours(
            intent, activities, restaurants
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
