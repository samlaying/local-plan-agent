"""
PlanningNode — 根据 Retrieval Node 的候选 POI，调用 LLM 生成 2-3 个候选行程方案。

核心流程：
1. 将候选 POI 序列化为文本，构建 LLM prompt
2. 如果存在 verifier_rejection_reason，在 prompt 中明确指出上一轮问题
3. LLM 返回 JSON，包含每个方案选择的 POI id 和顺序
4. 根据 LLM 选择从 retrieval_result 中找到对应 POI 对象
5. 复用 activity_workflow 中的 _build_plan / generate_actions 组装完整 PlanSchema
6. 降级：LLM 失败时回退到纯规则的 generate_plans

节点约束：
- 继承 BaseNode，通过构造函数接收 LLMClient
- 向 state.trace 追加 TraceEvent
- 不直接访问数据库或 HTTP
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, RetrievalResult, TraceEvent
from app.schemas.planning import PlanSchema, POISchema, UserIntentSchema
from app.services.activity_workflow import (
    ConstraintCheckResult,
    _build_plan,
    generate_actions,
    generate_plans,
)
from llm.base import LLMClient, LLMError, LLMMessage
from llm.structured_output import LLMParseError, parse_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM prompt 常量
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一位专业的本地生活行程规划专家。你的任务是根据候选地点列表，为用户生成 2-3 个不同风格的行程方案。

要求：
1. 每个方案必须选择一个主要活动地点和一个餐厅
2. 方案之间风格应有所区别（如：强度不同、距离远近不同、价格档次不同）
3. 选择时优先考虑：评分高、等位时间短、适合该场景的地点
4. 餐厅选择要与活动地点的位置和风格协调
5. 输出必须是合法 JSON，不含其他内容

输出格式（JSON 数组，每个元素是一个方案）：
{
  "plans": [
    {
      "plan_title": "方案标题（简短描述风格）",
      "plan_summary": "一句话描述方案亮点",
      "selected_activity_id": "主活动 POI 的 id",
      "selected_restaurant_id": "餐厅 POI 的 id",
      "extra_activity_id": "可选的附加活动 POI id，没有则为 null"
    }
  ]
}

注意：
- selected_activity_id、selected_restaurant_id 必须从候选列表中选择，使用完整 id 字段值
- extra_activity_id 可为 null，填入时也必须从活动候选列表中选择
- 最多生成 3 个方案，至少生成 2 个方案
"""

_REJECTION_HINT_TEMPLATE = """\

[上一轮方案被拒绝]
上一轮生成的方案存在以下问题，请在本次生成时避免：
{reason}

请重新选择地点和组合方式，确保新方案不再出现上述问题。
"""

_REQUIRED_FIELDS = ["plans"]

# ---------------------------------------------------------------------------
# POI 序列化
# ---------------------------------------------------------------------------

def _serialize_poi_list(pois: list[POISchema], label: str) -> str:
    """将 POI 列表序列化为可读文本，供 LLM 消费。"""
    if not pois:
        return f"[{label}：无候选]\n"

    lines = [f"[{label}候选列表]\n"]
    for poi in pois:
        lines.append(
            f"- id: {poi.id}\n"
            f"  名称: {poi.name}\n"
            f"  类别: {poi.subcategory}\n"
            f"  评分: {poi.rating}/5\n"
            f"  距离: {poi.distance_km}km（预计行程 {poi.travel_minutes} 分钟）\n"
            f"  营业时间: {poi.business_hours.open}–{poi.business_hours.close}\n"
            f"  推荐游玩时长: {poi.recommended_duration_minutes} 分钟\n"
            f"  人均费用: {poi.price_per_person} 元\n"
            f"  当前等位: {poi.queue.wait_minutes} 分钟\n"
            f"  可预约: {'是' if poi.reservable else '否'}\n"
        )
    return "".join(lines)


def _format_time_window(intent: UserIntentSchema) -> str:
    """
    将时间窗口格式化为可读字符串。

    - 若 start 和 end 均不为 None，返回 "YYYY-MM-DD HH:MM–HH:MM"
    - 否则，用 label（如 "下午"）或 duration_hours_min/max（如 "4–6小时"）作为替代，
      避免在 prompt 中出现无意义的 "None–None"。
    """
    tw = intent.time_window
    if tw.start is not None and tw.end is not None:
        return f"{tw.date} {tw.start}–{tw.end}"

    # 降级：使用 label 或时长范围描述时间窗口
    if tw.label:
        return f"{tw.date} {tw.label}"
    return f"{tw.date}（约 {intent.duration_hours_min}–{intent.duration_hours_max} 小时）"


def _build_user_message(
    intent: UserIntentSchema,
    retrieval: RetrievalResult,
    rejection_reason: str | None,
) -> str:
    """构建发送给 LLM 的用户消息内容。"""
    parts: list[str] = []

    parts.append(
        f"用户需求：{intent.raw_text}\n"
        f"场景：{intent.scenario}\n"
        f"出行时间：{_format_time_window(intent)}\n"
        f"出行时长：{intent.duration_hours_min}–{intent.duration_hours_max} 小时\n"
        f"出行方式：{intent.travel_mode}\n"
        f"最大距离：{intent.max_distance_km}km\n"
    )

    if intent.diet_requirements:
        parts.append(f"饮食要求：{', '.join(intent.diet_requirements)}\n")

    parts.append("\n")
    parts.append(_serialize_poi_list(retrieval.activities, "活动"))
    parts.append("\n")
    parts.append(_serialize_poi_list(retrieval.restaurants, "餐厅"))

    if rejection_reason:
        parts.append(_REJECTION_HINT_TEMPLATE.format(reason=rejection_reason))

    parts.append("\n请根据以上候选列表生成 2-3 个行程方案，以 JSON 格式返回。")
    return "".join(parts)


# ---------------------------------------------------------------------------
# LLM 响应解析与方案构建
# ---------------------------------------------------------------------------

def _find_poi(poi_id: str, poi_map: dict[str, POISchema]) -> POISchema | None:
    """从 POI 索引中查找指定 id 的 POI。"""
    return poi_map.get(poi_id)


def _build_poi_map(retrieval: RetrievalResult) -> dict[str, POISchema]:
    """构建 id -> POISchema 索引，供快速查找。"""
    return {poi.id: poi for poi in [*retrieval.activities, *retrieval.restaurants]}


def _plans_from_llm_response(
    llm_data: dict[str, Any],
    intent: UserIntentSchema,
    retrieval: RetrievalResult,
    poi_map: dict[str, POISchema],
) -> list[PlanSchema]:
    """
    根据 LLM 返回的方案选择结果，组装完整的 PlanSchema 列表。

    如果某个方案引用了不存在的 POI id，则跳过该方案。
    """
    raw_plans: list[dict[str, Any]] = llm_data.get("plans", [])
    if not isinstance(raw_plans, list):
        logger.warning("PlanningNode: LLM 响应 plans 字段不是列表，跳过 LLM 结果")
        return []

    plans: list[PlanSchema] = []
    for idx, raw in enumerate(raw_plans[:3], start=1):
        activity_id = raw.get("selected_activity_id", "")
        restaurant_id = raw.get("selected_restaurant_id", "")
        extra_id = raw.get("extra_activity_id")  # 可能为 None

        activity = _find_poi(activity_id, poi_map)
        restaurant = _find_poi(restaurant_id, poi_map)

        if activity is None or restaurant is None:
            logger.warning(
                "PlanningNode: 方案 %d 引用了无效 POI id（activity=%r, restaurant=%r），跳过",
                idx, activity_id, restaurant_id,
            )
            continue

        extra: POISchema | None = None
        if extra_id:
            extra = _find_poi(extra_id, poi_map)
            if extra is None:
                logger.warning(
                    "PlanningNode: 方案 %d 引用了无效 extra_activity_id=%r，忽略附加活动",
                    idx, extra_id,
                )

        plan = _build_plan(intent, activity, restaurant, extra, idx)

        # 将 LLM 的描述性字段覆盖到方案上（如果 LLM 提供了的话）
        plan_title = raw.get("plan_title", "").strip()
        plan_summary = raw.get("plan_summary", "").strip()
        if plan_title:
            plan = plan.model_copy(update={"title": plan_title})
        if plan_summary:
            plan = plan.model_copy(update={"summary": plan_summary})

        plans.append(plan)

    return plans


# ---------------------------------------------------------------------------
# PlanningNode
# ---------------------------------------------------------------------------

class PlanningNode(BaseNode):
    """
    Planning Node — LLM 驱动的行程方案生成节点。

    输入（从 state 读取）：
      - state.retrieval: RetrievalResult（活动和餐厅候选列表）
      - state.intent: UserIntentSchema（用户约束）
      - state.verifier_rejection_reason: str | None（上一轮被拒绝的原因）

    输出（写入 state）：
      - state.candidate_plans: list[PlanSchema]（2-3 个候选方案，含 actions）
      - state.trace: 追加 running / done / error TraceEvent

    降级策略：
      LLM 调用失败或响应解析失败时，自动回退到 generate_plans()（纯规则方式），
      确保系统在 LLM 不可用时仍能正常工作。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    @property
    def name(self) -> str:
        return "planning_node"

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="正在生成行程方案...",
        ))

        intent = state.intent
        retrieval = state.retrieval

        if intent is None or retrieval is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message="缺少必要输入：intent 或 retrieval 为空，无法生成方案",
            ))
            return state

        plans = await self._generate_with_llm(intent, retrieval, state.verifier_rejection_reason)

        if not plans:
            # LLM 路径失败，回退到规则方式
            logger.info("PlanningNode: LLM 路径未产生有效方案，回退到规则生成")
            state.trace.append(TraceEvent(
                agent=self.name,
                status="running",
                message="LLM 生成失败，回退到规则方式生成方案...",
            ))
            plans = self._fallback_generate(intent, retrieval)

        # 为每个方案生成可执行动作列表
        plans = generate_actions(intent, plans)

        state.candidate_plans = plans
        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=f"已生成 {len(plans)} 个候选方案",
        ))
        return state

    # ------------------------------------------------------------------
    # LLM 路径
    # ------------------------------------------------------------------

    async def _generate_with_llm(
        self,
        intent: UserIntentSchema,
        retrieval: RetrievalResult,
        rejection_reason: str | None,
    ) -> list[PlanSchema]:
        """调用 LLM 生成方案选择，然后组装 PlanSchema。失败时返回空列表。"""
        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_build_user_message(intent, retrieval, rejection_reason),
            ),
        ]

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._llm.chat(
                    messages,
                    temperature=0.7,
                    max_tokens=1024,
                    json_mode=True,
                ),
            )
        except LLMError as exc:
            logger.warning("PlanningNode: LLM 调用失败: %s", exc)
            return []

        try:
            llm_data = parse_json_response(response, required_fields=_REQUIRED_FIELDS)
        except LLMParseError as exc:
            logger.warning("PlanningNode: LLM 响应解析失败: %s | raw=%r", exc, exc.raw_content[:200])
            return []

        poi_map = _build_poi_map(retrieval)
        plans = _plans_from_llm_response(llm_data, intent, retrieval, poi_map)

        if not plans:
            logger.warning("PlanningNode: LLM 返回数据未能产生有效方案")

        return plans

    # ------------------------------------------------------------------
    # 规则降级路径
    # ------------------------------------------------------------------

    def _fallback_generate(
        self,
        intent: UserIntentSchema,
        retrieval: RetrievalResult,
    ) -> list[PlanSchema]:
        """
        回退到已有的纯规则方案生成逻辑（generate_plans）。

        将 RetrievalResult 转换为 ConstraintCheckResult（不再做过滤，
        直接将 retrieval 的候选集作为 accepted 使用）。
        """
        checked = ConstraintCheckResult(
            activities=retrieval.activities,
            restaurants=retrieval.restaurants,
            rejected=[],
        )
        return generate_plans(intent, checked)
