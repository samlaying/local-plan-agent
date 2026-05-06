"""
RetrievalNode — 并行检索活动、餐厅、天气、路线、营业时间信息。

并行执行 5 个子任务（asyncio.gather），将结果合并为 RetrievalResult 写入 state.retrieval。

子任务：
  1. 活动搜索    — 按 scenario 和 city 过滤活动类 POI
  2. 餐厅搜索    — 按 scenario 和饮食要求过滤餐厅 POI
  3. 天气查询    — mock：固定字符串，预留真实 API 接口
  4. 路线距离    — 从 routes.json 或 POI.travel_minutes 整理路线信息
  5. 营业时间检查 — 检查候选 POI 是否在用户时间窗口内营业，不营业的标记为 rejected

节点在 state.trace 追加两条 TraceEvent：running（开始前）和 done（完成后）。

多策略 ReAct 循环：
  针对每个 style_hint（如"亲子户外"、"文化艺术"、"休闲社交"），启动一个独立上下文的
  LLM ReAct 循环。LLM 先生成搜索关键词，执行搜索后观察结果，若候选数量不足则迭代
  调整关键词，最多 3 轮。3 个策略并行运行，上下文完全隔离。

同步 IO 处理：
  MockPOIRepository 的方法（list_activities / list_restaurants / list_all）和
  routes.json 的文件读取均为同步阻塞 IO。在 async def 协程中直接调用会阻塞
  event loop，导致 asyncio.create_task 的"并行"实际串行执行。
  修复方案：所有同步 IO 调用均通过 asyncio.get_running_loop().run_in_executor(None, ...)
  放入默认线程池执行，实现真正的并发。
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
    """并行执行 5 个检索子任务，将结果合并为 RetrievalResult 写入 state.retrieval。

    同时并行运行 3 个独立上下文的 LLM ReAct 策略循环，生成 retrieval_strategies。

    依赖注入：
      searcher    — AbstractPOISearcher（MockPOISearcher 或 AmapSearcher）
      llm_client  — LLMClient（用于策略 ReAct 循环中动态生成关键词）
      repository  — MockPOIRepository（或后续真实 POI 适配器）
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
        self._repository = repository or MockPOIRepository()
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
            message="开始并行检索活动、餐厅、天气、路线和营业时间...",
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

        # 并行运行 5 个子任务
        activities_task = asyncio.create_task(self._fetch_activities(intent))
        restaurants_task = asyncio.create_task(self._fetch_restaurants(intent))
        weather_task = asyncio.create_task(self._fetch_weather(intent))
        routes_task = asyncio.create_task(self._fetch_routes(intent))
        # 营业时间检查需要先拿到候选列表，必须等 activities/restaurants 完成
        # 但为了真正并行，先让 activity/restaurant 任务同时跑，再单独做检查。
        # 这里用 gather 等待前 4 个任务，再执行第 5 个（依赖前两个结果）。
        activities, restaurants, weather, route_info = await asyncio.gather(
            activities_task,
            restaurants_task,
            weather_task,
            routes_task,
        )

        # 子任务 5：营业时间检查（在前两个结果已知后执行）
        open_activities, open_restaurants, rejected = await self._check_business_hours(
            intent, activities, restaurants
        )

        state.retrieval = RetrievalResult(
            activities=open_activities,
            restaurants=open_restaurants,
            weather=weather,
            route_info=route_info,
        )

        # 多策略 ReAct 并行搜索：每个策略独立上下文，供 PlanningNode 独立规划
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

        logger.info(
            "[%s] strategy retrieval done: %d strategies, sizes=%s",
            self.name,
            len(state.retrieval_strategies),
            [(len(r.activities), len(r.restaurants)) for r in state.retrieval_strategies],
        )

        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=(
                f"检索完成：{len(open_activities)} 个活动，{len(open_restaurants)} 个餐厅，"
                f"天气：{weather}，"
                f"{len(rejected)} 个 POI 因营业时间被排除，"
                f"{len(state.retrieval_strategies)} 个策略候选集已并行获取"
            ),
        ))
        logger.info(
            "[%s] retrieval done: %d activities, %d restaurants, %d rejected",
            self.name, len(open_activities), len(open_restaurants), len(rejected),
        )
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
    # 子任务 1：活动搜索
    # ------------------------------------------------------------------

    async def _fetch_activities(self, intent: UserIntentSchema) -> list[POISchema]:
        """通过注入的 searcher 获取活动候选列表。

        searcher.search_activities() 是同步方法，用 run_in_executor 放入线程池
        避免阻塞 event loop，实现与其他子任务的真正并发。
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, lambda: self._searcher.search_activities(intent)
        )

    # ------------------------------------------------------------------
    # 子任务 2：餐厅搜索
    # ------------------------------------------------------------------

    async def _fetch_restaurants(self, intent: UserIntentSchema) -> list[POISchema]:
        """通过注入的 searcher 获取餐厅候选列表，再叠加饮食要求过滤。

        searcher.search_restaurants() 是同步方法，用 run_in_executor 放入线程池
        避免阻塞 event loop，实现与其他子任务的真正并发。
        """
        loop = asyncio.get_running_loop()
        candidates: list[POISchema] = await loop.run_in_executor(
            None, lambda: self._searcher.search_restaurants(intent)
        )

        # 饮食要求过滤：diet_requirements 非空时，用 tags 匹配（与 searcher 无关的通用逻辑）
        if intent.diet_requirements:
            diet_tags = set(intent.diet_requirements)
            candidates = [
                poi for poi in candidates
                if diet_tags.intersection(poi.tags)
                # 若餐厅无任何饮食标签但 weight_loss_friendly 分数高，也放行
                or (
                    "weight_loss_friendly" in diet_tags
                    and poi.audience_fit.weight_loss_friendly >= 70
                )
            ]

        return candidates

    # ------------------------------------------------------------------
    # 子任务 3：天气查询（mock）
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
        """从 routes.json 整理路线信息，并补充 POI 的 travel_minutes 字段数据。

        routes.json 文件读取和 list_all() 均为同步 IO，通过 run_in_executor 放入
        线程池执行，避免阻塞 event loop。

        返回格式：
        {
          "origin": "...",
          "static_routes": [...],          # routes.json 原始条目
          "poi_travel_minutes": {          # poi_id -> travel_minutes（来自 POI 字段）
              "family_activity_001": 14,
              ...
          }
        }
        """
        loop = asyncio.get_running_loop()

        # 读取 routes.json（同步文件 IO，放入线程池）
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

        # list_all() 也是同步 IO（读两个 JSON 文件），同样放入线程池
        def _load_all_pois() -> list[POISchema]:
            return self._repository.list_all()

        static_routes, all_pois = await asyncio.gather(
            loop.run_in_executor(None, _load_routes),
            loop.run_in_executor(None, _load_all_pois),
        )

        # 从所有 POI 的 travel_minutes 字段汇总（按出发地 origin 整理）
        poi_travel_minutes: dict[str, int] = {
            poi.id: poi.travel_minutes
            for poi in all_pois
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        }

        return {
            "origin": intent.origin,
            "static_routes": static_routes,
            "poi_travel_minutes": poi_travel_minutes,
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
