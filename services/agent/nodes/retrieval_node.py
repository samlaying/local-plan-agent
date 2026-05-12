"""
RetrievalNode — 获取天气/路线信息（主路径）+ 提供 search_and_judge 方法供 PlanningNode 调用。

主路径（并行）：
  - 天气查询    — mock，预留真实 API
  - 路线信息    — 从 routes.json 读取静态路线（origin + static_routes）
  结果写入 state.retrieval（activities/restaurants 为空列表，仅 weather/route_info 有效）

search_and_judge() — 无状态逐调用搜索+质量判断方法：
  - 每个调用独立，不维护跨调用状态
  - 内部 ReAct 循环：搜索 -> LLM 判断质量 -> 如不合格则用建议关键词重试
  - LLM 是"评审者"角色：评估候选是否匹配风格、是否高质量、是否多样
  - 返回 SearchAndJudgeResult（候选列表 + 质量评估）

state.retrieval_strategies 现在仅包含风格方向（list of RetrievalResult with just style field），
由 PlanningNode 消费以驱动 3 个并行策略探索循环。
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
from agent.state.types import (
    PlanningState,
    QualityAssessment,
    RetrievalResult,
    SearchAndJudgeResult,
    TraceEvent,
)
from llm.base import LLMClient, LLMMessage
from llm.structured_output import LLMParseError, parse_json_response
from tools.poi.base import AbstractPOISearcher

logger = logging.getLogger(__name__)

# 默认关键词（LLM 不可用或解析失败时使用）
_DEFAULT_ACTIVITY_KEYWORDS = "景点|公园|休闲"
_DEFAULT_RESTAURANT_KEYWORDS = "餐厅"


# ---------------------------------------------------------------------------
# RetrievalNode
# ---------------------------------------------------------------------------

class RetrievalNode(BaseNode):
    """检索节点 — 主路径（天气+路线）+ search_and_judge 方法。

    主路径（并行）：
      - 天气查询    — mock，预留真实 API
      - 路线信息    — 从 routes.json 读取静态路线（origin + static_routes）

    search_and_judge()：
      无状态逐调用方法，供 PlanningNode._explore_one_style 调用：
      1. LLM 根据风格+意图生成搜索关键词（关键词为空时首次调用生成）
      2. 搜索候选 POI
      3. LLM 评估候选质量（风格匹配度、评分、多样性、充分性）
      4. 评价不通过且有改进方向时，用建议关键词重试（最多 2 次）
      5. 返回 SearchAndJudgeResult

    依赖注入：
      searcher    — AbstractPOISearcher（MockPOISearcher 或 AmapSearcher）
      llm_client  — LLMClient（用于关键词生成和质量评判）
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
        # services/agent/nodes/retrieval_node.py -> 上 3 级到项目根
        return Path(__file__).resolve().parents[3] / "data" / "mock" / "routes.json"

    # ------------------------------------------------------------------
    # BaseNode.run — 仅获取天气+路线+风格方向
    # ------------------------------------------------------------------

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="开始检索：天气、路线、策略方向...",
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

        # 主路径：天气 + 路线（并行）
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

        # 生成 3 个策略方向（供 PlanningNode 使用）
        scenario = intent.scenario if intent.scenario else ""
        style_hints = await self._generate_style_hints(intent, scenario)

        # 将风格方向写入 state
        state.style_hints = style_hints
        state.retrieval_strategies = [
            RetrievalResult(style=hint) for hint in style_hints
        ]

        logger.info(
            "[%s] retrieval done: weather=%s, %d style hints",
            self.name, weather, len(style_hints),
        )

        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=(
                f"检索完成：{len(style_hints)} 个策略方向，"
                f"天气：{weather}"
            ),
        ))
        return state

    # ------------------------------------------------------------------
    # search_and_judge — 无状态逐调用搜索 + 质量判断
    # ------------------------------------------------------------------

    async def search_and_judge(
        self,
        *,
        lat: float,
        lng: float,
        style: str,
        intent: UserIntentSchema,
        search_type: str = "activity",
        exclude_poi_ids: set[str] | None = None,
        radius_m: int | None = None,
        keywords: str | None = None,
        max_retries: int = 2,
        traces: list[TraceEvent] | None = None,
    ) -> SearchAndJudgeResult:
        """单次搜索 + 质量判断调用，无状态。

        流程：
          1. 如果需要，调用 LLM 生成初始搜索关键词
          2. 搜索候选 POI
          3. 排除已选 POI + 营业时间过滤
          4. LLM 评估候选质量
          5. 不通过且有改进方向时重试（最多 max_retries 次）
          6. 返回 SearchAndJudgeResult

        Args:
            lat:              搜索中心纬度。
            lng:              搜索中心经度。
            style:            当前策略方向。
            intent:           用户规划意图。
            search_type:      搜索类型，"activity" 或 "restaurant"。
            exclude_poi_ids:  需要排除的 POI ID 集合。
            radius_m:         搜索半径（米），默认使用 intent.max_distance_km。
            keywords:         搜索关键词；为 None 则首次调用 LLM 生成。
            max_retries:      重试最大次数（默认 2）。

        Returns:
            SearchAndJudgeResult。
        """
        loop = asyncio.get_running_loop()

        if radius_m is None:
            radius_m = int(intent.max_distance_km * 1000)
        if exclude_poi_ids is None:
            exclude_poi_ids = set()

        # 首次调用且未指定关键词时，由 LLM 生成
        if keywords is None:
            keywords = await self._generate_search_keywords(style, intent, search_type)

        is_activity = search_type == "activity"
        type_label = "活动" if is_activity else "餐厅"
        if traces is not None:
            traces.append(TraceEvent(
                agent=self.name,
                status="running",
                message=f"搜索{type_label}: keywords={keywords} radius={radius_m}m @ ({lat:.4f}, {lng:.4f})",
            ))

        for attempt in range(max_retries + 1):
            # --- 搜索候选 ---
            try:
                if is_activity:
                    raw_candidates: list[POISchema] = await loop.run_in_executor(
                        None,
                        lambda: self._searcher.search_activities_around(
                            lat, lng, keywords, radius_m, intent,
                        ),
                    )
                else:
                    raw_candidates = await loop.run_in_executor(
                        None,
                        lambda: self._searcher.search_restaurants_around(
                            lat, lng, keywords, radius_m, intent,
                        ),
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "[%s] search_and_judge: search failed (attempt %d/%d): %s",
                    self.name, attempt + 1, max_retries + 1, exc,
                )
                raw_candidates = []

            # --- 排除已选 POI ---
            candidates = [p for p in raw_candidates if p.id not in exclude_poi_ids]

            # --- 营业时间过滤 ---
            if candidates:
                if is_activity:
                    candidates, _, _ = await self._check_business_hours(
                        intent, candidates, [],
                    )
                else:
                    _, candidates, _ = await self._check_business_hours(
                        intent, [], candidates,
                    )

            # --- 无候选时直接返回空区域 ---
            if not candidates:
                return SearchAndJudgeResult(
                    candidates=[],
                    assessment=QualityAssessment(
                        passed=False,
                        score=0,
                        strengths=[],
                        weaknesses=["无候选POI"],
                        empty_area=True,
                        judge_reasoning="搜索未返回任何候选POI",
                    ),
                    search_center_lat=lat,
                    search_center_lng=lng,
                    search_type=search_type,
                    style=style,
                )

            # --- LLM 评估质量（LLM 不可用时按评分降序返回 top-5）---
            if self._llm_client is None:
                top_candidates = sorted(
                    candidates, key=lambda p: p.rating, reverse=True,
                )[:5]
                return SearchAndJudgeResult(
                    candidates=top_candidates,
                    assessment=QualityAssessment(
                        passed=True,
                        score=70,
                        strengths=["LLM 不可用，按评分降序排列"],
                        weaknesses=[],
                        judge_reasoning="LLM 不可用，按评分排序返回 top-5",
                    ),
                    search_center_lat=lat,
                    search_center_lng=lng,
                    search_type=search_type,
                    style=style,
                )

            assessment = await self._judge_candidates(
                candidates, style, intent, search_type,
            )

            if traces is not None:
                result_label = "通过" if assessment.passed else "未通过"
                detail_parts = [f"评分={assessment.score}"]
                if assessment.strengths:
                    detail_parts.append(f"优点: {assessment.strengths[0]}")
                if assessment.weaknesses:
                    detail_parts.append(f"缺点: {assessment.weaknesses[0]}")
                traces.append(TraceEvent(
                    agent=self.name,
                    status="done" if assessment.passed else "running",
                    message=f"LLM 评估{type_label}: {result_label} ({', '.join(detail_parts)})",
                ))

            if assessment.passed:
                return SearchAndJudgeResult(
                    candidates=candidates,
                    assessment=assessment,
                    search_center_lat=lat,
                    search_center_lng=lng,
                    search_type=search_type,
                    style=style,
                )

            if assessment.empty_area:
                return SearchAndJudgeResult(
                    candidates=candidates,
                    assessment=assessment,
                    search_center_lat=lat,
                    search_center_lng=lng,
                    search_type=search_type,
                    style=style,
                )

            # 不通过且有重试机会 + 建议关键词
            if attempt < max_retries and assessment.suggested_keywords:
                keywords = assessment.suggested_keywords
                if traces is not None:
                    traces.append(TraceEvent(
                        agent=self.name,
                        status="running",
                        message=f"重试 {attempt+1}: 改用 keywords={keywords}",
                    ))
                logger.debug(
                    "[%s] search_and_judge: retry %d with keywords=%r",
                    self.name, attempt + 1, keywords,
                )
                continue

            # 达到重试上限或无建议关键词，返回当前结果
            return SearchAndJudgeResult(
                candidates=candidates,
                assessment=assessment,
                search_center_lat=lat,
                search_center_lng=lng,
                search_type=search_type,
                style=style,
            )

        # 不应到达此处
        return SearchAndJudgeResult(
            candidates=[],
            assessment=QualityAssessment(
                passed=False, score=0, weaknesses=["search_and_judge 异常退出"],
                judge_reasoning="search_and_judge 循环异常结束",
            ),
            search_center_lat=lat,
            search_center_lng=lng,
            search_type=search_type,
            style=style,
        )

    async def _generate_search_keywords(
        self,
        style: str,
        intent: UserIntentSchema,
        search_type: str,
    ) -> str:
        """根据风格+意图生成搜索关键词。

        LLM 不可用时返回默认关键词。
        """
        if self._llm_client is None:
            return (
                _DEFAULT_ACTIVITY_KEYWORDS
                if search_type == "activity"
                else _DEFAULT_RESTAURANT_KEYWORDS
            )

        loop = asyncio.get_running_loop()
        type_label = "活动" if search_type == "activity" else "餐厅"
        system_content = (
            f"你是一个POI搜索关键词生成器。请根据用户的出行风格和意图，"
            f"生成适合搜索{type_label}的高德地图关键词。\n"
            "要求：\n"
            f"1. 关键词应贴合「{style}」风格方向\n"
            '2. 多个关键词用 | 分隔，如"公园|游乐场|自然"\n'
            "3. 关键词应具体、可搜索，避免泛泛的空洞词汇\n"
            '以 JSON 格式返回：{"keywords": "关键词字符串"}\n'
            "不要包含任何其他内容。"
        )

        participant_desc = ""
        if hasattr(intent, "participants") and intent.participants:
            participant_desc = f"，参与者：{intent.participants}"
        diet_desc = ""
        if hasattr(intent, "diet_requirements") and intent.diet_requirements:
            diet_desc = f"，饮食要求：{intent.diet_requirements}"

        user_content = (
            f"风格方向：{style}\n"
            f"城市：{getattr(intent, 'city', '未知')}\n"
            f"场景：{getattr(intent, 'scenario', '未知')}{participant_desc}\n"
            f"偏好：{getattr(intent, 'soft_preferences', [])}{diet_desc}\n"
            f"搜索类型：{type_label}\n"
            "请生成合适的高德搜索关键词。"
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
            parsed = parse_json_response(response, required_fields=["keywords"])
            keywords = str(parsed["keywords"])
            logger.debug(
                "[%s] _generate_search_keywords: style=%r type=%s -> %r",
                self.name, style, search_type, keywords,
            )
            return keywords
        except (LLMParseError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "[%s] _generate_search_keywords failed: %s, using default",
                self.name, exc,
            )
            return (
                _DEFAULT_ACTIVITY_KEYWORDS
                if search_type == "activity"
                else _DEFAULT_RESTAURANT_KEYWORDS
            )

    async def _judge_candidates(
        self,
        candidates: list[POISchema],
        style: str,
        intent: UserIntentSchema,
        search_type: str,
    ) -> QualityAssessment:
        """LLM 评审候选 POI 质量。

        评审维度：风格匹配度、评分阈值、类别多样性、数量充分性。
        评审者角色：判断这批候选是否足够好，不选择具体 POI。

        Args:
            candidates:   候选 POI 列表。
            style:        当前策略方向。
            intent:       用户规划意图。
            search_type:  搜索类型，"activity" 或 "restaurant"。

        Returns:
            QualityAssessment。
        """
        loop = asyncio.get_running_loop()

        # 序列化候选列表
        type_label = "活动" if search_type == "activity" else "餐厅"
        lines: list[str] = [f"候选{type_label}列表（共 {len(candidates)} 个）："]
        for i, poi in enumerate(candidates, 1):
            lines.append(
                f"  [{i}] {poi.name}（{poi.subcategory}）"
                f" | 评分 {poi.rating}/5"
                f" | 距搜索中心 {poi.distance_km:.1f}km"
                f" | 人均 {poi.price_per_person}元"
            )

        candidates_text = "\n".join(lines)

        # 构建参与者描述
        participant_parts: list[str] = []
        for p in intent.participants:
            desc = f"{p.type}×{p.count}"
            if p.age is not None:
                desc += f"（{p.age}岁）"
            if p.notes:
                desc += f"[{', '.join(p.notes)}]"
            participant_parts.append(desc)

        system_content = (
            "你是一位POI候选质量评审专家。你的任务是根据给定的风格方向和用户意图，"
            "评估一批POI候选项的质量。\n\n"
            "评估维度：\n"
            "1. 风格匹配度：这些POI是否符合指定的风格方向？\n"
            "2. 评分质量：POI评分是否普遍在3分以上？是否有过低评分的POI？\n"
            "3. 类别多样性：POI是否涵盖不同子类别，提供多样化选择？\n"
            "4. 数量充分性：候选数量是否足够让规划者从中选择？\n\n"
            "注意：\n"
            "- 你只评估质量，不选择具体POI\n"
            "- 如果质量不合格，请通过 suggested_keywords 提供更好的搜索关键词\n"
            "- 如果该区域真的缺乏POI（搜索已经很充分但没什么可选），设 empty_area=true\n\n"
            "请以JSON格式输出评估结果，格式如下：\n"
            '{\n'
            '  "passed": true/false,\n'
            '  "score": 0-100,\n'
            '  "strengths": ["优点1", "优点2"],\n'
            '  "weaknesses": ["缺点1", "缺点2"],\n'
            '  "suggested_keywords": "若未通过，建议的搜索关键词（用|分隔）；通过则为null",\n'
            '  "empty_area": false,\n'
            '  "judge_reasoning": "综合判断的理由（一句话）"\n'
            '}'
        )

        user_content = (
            f"风格方向：{style}\n"
            f"用户需求：{intent.raw_text}\n"
            f"场景：{intent.scenario}\n"
            f"参与人员：{'、'.join(participant_parts)}\n"
        )
        if intent.diet_requirements:
            user_content += f"饮食要求：{', '.join(intent.diet_requirements)}\n"
        if intent.soft_preferences:
            user_content += f"偏好：{', '.join(intent.soft_preferences)}\n"
        user_content += f"\n{candidates_text}\n\n请评估这批{type_label}候选的质量。"

        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ]

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._llm_client.chat(messages, json_mode=True),  # type: ignore[union-attr]
            )
            parsed = parse_json_response(response, required_fields=["passed", "score"])

            assessment = QualityAssessment(
                passed=bool(parsed["passed"]),
                score=int(parsed.get("score", 50)),
                strengths=parsed.get("strengths", []),
                weaknesses=parsed.get("weaknesses", []),
                suggested_keywords=parsed.get("suggested_keywords"),
                empty_area=bool(parsed.get("empty_area", False)),
                judge_reasoning=str(parsed.get("judge_reasoning", "")),
            )

            logger.debug(
                "[%s] _judge_candidates: passed=%s score=%d empty=%s",
                self.name, assessment.passed, assessment.score, assessment.empty_area,
            )
            return assessment

        except (LLMParseError, Exception) as exc:  # noqa: BLE001
            logger.warning(
                "[%s] _judge_candidates failed: %s, returning default pass",
                self.name, exc,
            )
            # 解析失败时默认通过（不阻塞流程）
            return QualityAssessment(
                passed=True,
                score=60,
                strengths=[],
                weaknesses=[f"LLM 评审解析失败: {exc}"],
                judge_reasoning="LLM 评审解析失败，默认通过",
            )

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

        except (LLMParseError, Exception) as exc:  # noqa: BLE001
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
    # 坐标系解析
    # ------------------------------------------------------------------

    async def _resolve_origin(self, intent: UserIntentSchema) -> tuple[float, float]:
        """将出发地地址解析为 (lat, lng) 坐标对。

        底层委托 searcher.geocode()，该方法在 run_in_executor 中执行以避免阻塞。
        AmapSearcher 会发起真实 HTTP 请求；MockPOISearcher 返回硬编码坐标。

        解析失败时降级为上海人民广场坐标（31.2304, 121.4737）。
        """
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                lambda: self._searcher.geocode(intent.origin, intent.city),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[%s] geocode failed for %r (city=%s): %s，降级为默认坐标",
                self.name, intent.origin, intent.city, exc,
            )
            return (31.2304, 121.4737)

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
    # 路线距离
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

        注意：此处不再构建 poi_id -> travel_minutes 映射。各 POI 的出行时间
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
    # 营业时间 / 库存检查
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
