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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RetrievalNode
# ---------------------------------------------------------------------------

class RetrievalNode(BaseNode):
    """并行执行 5 个检索子任务，将结果合并为 RetrievalResult 写入 state.retrieval。

    依赖注入：
      repository  — MockPOIRepository（或后续真实 POI 适配器）
      routes_path — routes.json 文件路径；None 时自动从项目根目录推断
    """

    def __init__(
        self,
        repository: MockPOIRepository | None = None,
        routes_path: Path | None = None,
    ) -> None:
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

        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=(
                f"检索完成：{len(open_activities)} 个活动，{len(open_restaurants)} 个餐厅，"
                f"天气：{weather}，"
                f"{len(rejected)} 个 POI 因营业时间被排除"
            ),
        ))
        logger.info(
            "[%s] retrieval done: %d activities, %d restaurants, %d rejected",
            self.name, len(open_activities), len(open_restaurants), len(rejected),
        )
        return state

    # ------------------------------------------------------------------
    # 子任务 1：活动搜索
    # ------------------------------------------------------------------

    async def _fetch_activities(self, intent: UserIntentSchema) -> list[POISchema]:
        """从 MockPOIRepository 按 scenario 和 city 过滤活动类 POI。"""
        all_activities = self._repository.list_activities()
        return [
            poi for poi in all_activities
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        ]

    # ------------------------------------------------------------------
    # 子任务 2：餐厅搜索
    # ------------------------------------------------------------------

    async def _fetch_restaurants(self, intent: UserIntentSchema) -> list[POISchema]:
        """从 MockPOIRepository 按 scenario 和饮食要求过滤餐厅 POI。"""
        all_restaurants = self._repository.list_restaurants()
        candidates = [
            poi for poi in all_restaurants
            if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
        ]

        # 饮食要求过滤：diet_requirements 非空时，用 tags 匹配
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

        返回格式：
        {
          "static_routes": [...],          # routes.json 原始条目
          "poi_travel_minutes": {          # poi_id -> travel_minutes（来自 POI 字段）
              "family_activity_001": 14,
              ...
          }
        }
        """
        # 读取 routes.json（同步 IO，数据量小，不必放线程池）
        static_routes: list[dict[str, Any]] = []
        try:
            with self._routes_path.open("r", encoding="utf-8") as f:
                static_routes = json.load(f)
        except FileNotFoundError:
            logger.warning("[%s] routes.json not found at %s", self.name, self._routes_path)
        except json.JSONDecodeError as exc:
            logger.warning("[%s] routes.json parse error: %s", self.name, exc)

        # 从所有 POI 的 travel_minutes 字段汇总（按出发地 origin 整理）
        all_pois = self._repository.list_all()
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
