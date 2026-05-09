"""
PlanningNode — 根据 Retrieval Node 的候选 POI，调用 LLM 生成 2-3 个候选行程方案。

核心流程：
1. 将候选 POI 序列化为文本，构建 LLM prompt
2. 如果存在 verifier_rejection_reason，在 prompt 中明确指出上一轮问题
3. 如果存在 preference_adjustments，在 prompt 末尾追加用户偏好调整要求
4. LLM 返回 JSON，包含每个方案选择的 POI id 和顺序
5. 根据 LLM 选择从 retrieval_result 中找到对应 POI 对象
6. 复用 activity_workflow 中的 _build_plan_from_steps / generate_actions 组装完整 PlanSchema
7. 降级：LLM 失败时回退到纯规则的 generate_plans

节点约束：
- 继承 BaseNode，通过构造函数接收 LLMClient
- 向 state.trace 追加 TraceEvent
- 不直接访问数据库或 HTTP
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, RetrievalResult, TraceEvent
from app.schemas.planning import ItineraryStepSchema, PlanSchema, POISchema, UserIntentSchema
from app.services.activity_workflow import (
    ConstraintCheckResult,
    _build_plan_from_steps,
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
1. 方案之间风格应有所区别（如：强度不同、距离远近不同、价格档次不同）
2. 选择时优先考虑：评分高、等位时间短、适合该场景的地点
3. 输出必须是合法 JSON，不含其他内容
4. 时间决策：你需要为每个地点决定合理的停留时长。\
依据场景特征（亲子/朋友）、参与人群（有孩子则时间更短）和总时间窗口综合判断。\
时长约束：活动类建议 45–120 分钟，餐厅类建议 40–80 分钟。\
确保所有地点时长之和加上出行时间（约 10–20 分钟）不超过时间窗口总长。\
如果时间窗口有剩余（≥ 30 分钟），优先增加一个活动地点，而不是让时间空着。
5. 活动数量根据时间窗口决定：
   - 总时长 ≥ 6 小时：至少 2 个活动
   - 总时长 ≥ 8 小时：至少 3 个活动
   - 充分利用时间窗口，不要空着。
6. 步骤描述：为每个地点写一句具体的中文描述，说明在这里做什么、有什么亮点，写给用户看的，不超过 30 字。
7. 全中文输出：所有文本字段必须使用中文，POI 的原始英文名称可保留。
8. 用餐规则：
   - 如果用户消息中写明"需要安排用餐"，steps 中必须包含至少一个 type=meal 的步骤，用餐位置根据时间窗口合理决定。
   - 如果用户消息中写明"不需要安排用餐，候选列表中无餐厅"，steps 全部为 activity，不出现 meal。

输出格式（JSON，plans 数组包含 2-3 个方案，每个方案 steps 为数组，每项含 poi_id/type/duration_minutes/description）。

注意：
- steps 中每项的 poi_id 必须从候选列表中选择，使用完整 id 字段值
- type 只能是 "activity" 或 "meal"
- 最多生成 3 个方案，至少生成 2 个方案
"""

_REJECTION_HINT_TEMPLATE = """\

[上一轮方案被拒绝]
上一轮生成的方案存在以下问题，请在本次生成时避免：
{reason}

请重新选择地点和组合方式，确保新方案不再出现上述问题。
"""

_PREFERENCE_ADJUSTMENTS_TEMPLATE = """\

[用户偏好调整]
用户对上一版方案提出了以下调整要求，请在本次方案中满足：
{adjustments}
"""

_SINGLE_PLAN_SYSTEM_PROMPT = """\
你是一位专业的本地生活行程规划专家。你的任务是根据候选地点列表，为用户生成 1 个最优行程方案。

要求：
1. 选择时优先考虑：评分高、等位时间短、适合该场景的地点
2. 输出必须是合法 JSON，不含其他内容
3. 时间决策：你需要为每个地点决定合理的停留时长。\
依据场景特征（亲子/朋友）、参与人群（有孩子则时间更短）和总时间窗口综合判断。\
时长约束：活动类建议 45–120 分钟，餐厅类建议 40–80 分钟。\
确保所有地点时长之和加上出行时间（约 10–20 分钟）不超过时间窗口总长。\
如果时间窗口有剩余（≥ 30 分钟），优先增加一个活动地点，而不是让时间空着。
4. 活动数量根据时间窗口决定：
   - 总时长 ≥ 6 小时：至少 2 个活动
   - 总时长 ≥ 8 小时：至少 3 个活动
   - 充分利用时间窗口，不要空着。
5. 步骤描述：为每个地点写一句具体的中文描述，说明在这里做什么、有什么亮点，写给用户看的，不超过 30 字。
6. 全中文输出：所有文本字段必须使用中文，POI 的原始英文名称可保留。
7. 用餐规则：
   - 如果用户消息中写明"需要安排用餐"，steps 中必须包含至少一个 type=meal 的步骤，用餐位置根据时间窗口合理决定。
   - 如果用户消息中写明"不需要安排用餐，候选列表中无餐厅"，steps 全部为 activity，不出现 meal。

输出格式（JSON，plans 数组包含 1 个方案，方案 steps 为数组，每项含 poi_id/type/duration_minutes/description）。

注意：
- steps 中每项的 poi_id 必须从候选列表中选择，使用完整 id 字段值
- type 只能是 "activity" 或 "meal"
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
    preference_adjustments: list[str] | None = None,
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

    include_meal = getattr(intent, "include_meal", True)
    if include_meal:
        parts.append("用餐安排：需要安排用餐\n")
    else:
        parts.append("用餐安排：不需要安排用餐，候选列表中无餐厅\n")

    parts.append("\n")
    parts.append(_serialize_poi_list(retrieval.activities, "活动"))
    parts.append("\n")
    parts.append(_serialize_poi_list(retrieval.restaurants, "餐厅"))

    if rejection_reason:
        parts.append(_REJECTION_HINT_TEMPLATE.format(reason=rejection_reason))

    if preference_adjustments:
        adjustments_text = "\n".join(f"- {item}" for item in preference_adjustments)
        parts.append(_PREFERENCE_ADJUSTMENTS_TEMPLATE.format(adjustments=adjustments_text))

    parts.append("\n请根据以上候选列表生成 2-3 个行程方案，以 JSON 格式返回。")
    return "".join(parts)


def _build_user_message_single(
    intent: UserIntentSchema,
    retrieval: RetrievalResult,
    style: str,
    rejection_reason: str | None = None,
    preference_adjustments: list[str] | None = None,
) -> str:
    """构建单策略 LLM 调用的用户消息，包含风格说明，要求只生成 1 个方案。"""
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

    include_meal = getattr(intent, "include_meal", True)
    if include_meal:
        parts.append("用餐安排：需要安排用餐\n")
    else:
        parts.append("用餐安排：不需要安排用餐，候选列表中无餐厅\n")

    if style:
        parts.append(f"当前风格：{style}\n")

    parts.append("\n")
    parts.append(_serialize_poi_list(retrieval.activities, "活动"))
    parts.append("\n")
    parts.append(_serialize_poi_list(retrieval.restaurants, "餐厅"))

    if rejection_reason:
        parts.append(_REJECTION_HINT_TEMPLATE.format(reason=rejection_reason))

    if preference_adjustments:
        adjustments_text = "\n".join(f"- {item}" for item in preference_adjustments)
        parts.append(_PREFERENCE_ADJUSTMENTS_TEMPLATE.format(adjustments=adjustments_text))

    parts.append("\n请从以上候选列表中选出 1 个最优方案，以 JSON 格式返回。")
    return "".join(parts)


# ---------------------------------------------------------------------------
# 中文本地化：将 _build_plan_from_steps 生成的英文描述替换为中文
# ---------------------------------------------------------------------------

def _localize_step(step: ItineraryStepSchema, poi_map: dict[str, POISchema]) -> ItineraryStepSchema:
    """将单个行程步骤中的英文描述替换为中文。"""
    desc = step.description

    # 替换 "estimated queue X minutes" → "预计等位 X 分钟"
    desc = re.sub(
        r"estimated queue\s+(\d+)\s+minutes?",
        lambda m: f"预计等位 {m.group(1)} 分钟",
        desc,
        flags=re.IGNORECASE,
    )

    # 替换 "Estimated local travel time based on mock POI data."
    desc = re.sub(
        r"Estimated local travel time based on mock POI data\.?",
        "预计本地出行时间（基于模拟数据）。",
        desc,
        flags=re.IGNORECASE,
    )

    # 替换 step description 中的分号分隔的子类别描述，如 "亲子活动; estimated queue 0 minutes."
    # 已由上方两条规则处理，此处保留分号清理
    desc = desc.strip()

    return step.model_copy(update={"description": desc})


def _localize_fit_summary(intent: UserIntentSchema, extra_poi: POISchema | None) -> list[str]:
    """生成中文版 fit_summary，替代 _build_plan_from_steps 生成的英文版本。"""
    if intent.scenario == "family_weight_loss_child5":
        summary = [
            "主要活动适合 5 岁孩子参与。",
            "餐厅提供适合减脂需求的健康餐食选项。",
        ]
    else:
        summary = [
            "活动适合四人朋友同行。",
            "餐厅适合混合性别小组用餐和聊天。",
        ]
    if extra_poi is not None:
        summary.append("附加活动可根据时间和排队情况灵活决定是否参与。")
    return summary


def _localize_plan(
    plan: PlanSchema,
    intent: UserIntentSchema,
    extra_poi: POISchema | None,
    poi_map: dict[str, POISchema],
) -> PlanSchema:
    """对 _build_plan_from_steps 输出的方案进行中文本地化处理。

    处理内容：
    - 将 steps 中的英文 description 替换为中文
    - 将 fit_summary 替换为中文版本
    """
    localized_steps = [_localize_step(step, poi_map) for step in plan.steps]
    localized_fit_summary = _localize_fit_summary(intent, extra_poi)
    return plan.model_copy(update={
        "steps": localized_steps,
        "fit_summary": localized_fit_summary,
    })



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
    根据 LLM 返回的 steps 列表方案结果，组装完整的 PlanSchema 列表。

    LLM 输出格式：
        {"plans": [{"plan_title": "...", "plan_summary": "...", "steps": [
            {"poi_id": "...", "type": "activity"|"meal", "duration_minutes": N, "description": "..."},
            ...
        ]}, ...]}

    如果某个方案的 steps 引用了不存在的 POI id，则跳过该方案。
    """
    raw_plans: list[dict[str, Any]] = llm_data.get("plans", [])
    if not isinstance(raw_plans, list):
        logger.warning("PlanningNode: LLM 响应 plans 字段不是列表，跳过 LLM 结果")
        return []

    plans: list[PlanSchema] = []
    for idx, raw in enumerate(raw_plans[:3], start=1):
        raw_steps = raw.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            logger.warning("PlanningNode: 方案 %d 缺少 steps 列表，跳过", idx)
            continue

        # 解析 steps，查找对应 POI
        steps_spec: list[dict] = []
        valid = True
        for step_item in raw_steps:
            if not isinstance(step_item, dict):
                logger.warning("PlanningNode: 方案 %d 的 step 不是 dict，跳过方案", idx)
                valid = False
                break

            poi_id = step_item.get("poi_id", "")
            step_type = step_item.get("type", "activity")
            if step_type not in ("activity", "meal"):
                logger.warning(
                    "PlanningNode: 方案 %d step type=%r 非法，重置为 activity", idx, step_type,
                )
                step_type = "activity"

            poi = _find_poi(poi_id, poi_map)
            if poi is None:
                logger.warning(
                    "PlanningNode: 方案 %d 引用了无效 poi_id=%r，跳过方案", idx, poi_id,
                )
                valid = False
                break

            raw_dur = step_item.get("duration_minutes")
            duration_minutes: int = (
                int(raw_dur) if isinstance(raw_dur, (int, float)) and raw_dur > 0
                else poi.recommended_duration_minutes
            )
            desc = step_item.get("description", "")
            description: str | None = desc.strip() if isinstance(desc, str) and desc.strip() else None

            steps_spec.append({
                "poi": poi,
                "type": step_type,
                "duration_minutes": duration_minutes,
                "description": description,
            })

        if not valid or not steps_spec:
            continue

        plan = _build_plan_from_steps(intent, steps_spec, idx)

        # 将 LLM 提供的标题/摘要覆盖到方案上
        plan_title = raw.get("plan_title", "")
        plan_summary = raw.get("plan_summary", "")
        if isinstance(plan_title, str) and plan_title.strip():
            plan = plan.model_copy(update={"title": plan_title.strip()})
        if isinstance(plan_summary, str) and plan_summary.strip():
            plan = plan.model_copy(update={"summary": plan_summary.strip()})

        # 本地化 transit 步骤的英文描述
        plan = _localize_plan(plan, intent, None, poi_map)

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
      - state.preference_adjustments: list[str]（用户偏好调整指令）

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

        if intent is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message="缺少必要输入：intent 为空，无法生成方案",
            ))
            return state

        rejection_reason = state.verifier_rejection_reason
        preference_adjustments = state.preference_adjustments or None

        if state.retrieval_strategies:
            # 新路径：每个策略独立生成 1 个方案，并行执行
            plans = await self._plan_from_strategies(
                intent,
                state.retrieval_strategies,
                rejection_reason,
                preference_adjustments,
            )
        else:
            # 旧路径：从单一候选池让 LLM 选出 2-3 个方案（向后兼容）
            if retrieval is None:
                state.trace.append(TraceEvent(
                    agent=self.name,
                    status="error",
                    message="缺少必要输入：retrieval 为空，无法生成方案",
                ))
                return state
            plans = await self._generate_with_llm(
                intent,
                retrieval,
                rejection_reason,
                preference_adjustments,
            )

        if not plans:
            # LLM 路径失败，回退到规则方式
            # 多策略路径：从 retrieval_strategies 聚合所有候选 POI 构造合并候选池
            # 旧路径：直接使用 state.retrieval
            if state.retrieval_strategies:
                merged_activities: list = []
                merged_restaurants: list = []
                seen_ids: set[str] = set()
                for strategy in state.retrieval_strategies:
                    for poi in strategy.activities:
                        if poi.id not in seen_ids:
                            merged_activities.append(poi)
                            seen_ids.add(poi.id)
                    for poi in strategy.restaurants:
                        if poi.id not in seen_ids:
                            merged_restaurants.append(poi)
                            seen_ids.add(poi.id)
                fallback_retrieval = RetrievalResult(
                    activities=merged_activities,
                    restaurants=merged_restaurants,
                )
            elif retrieval is not None:
                fallback_retrieval = retrieval
            else:
                fallback_retrieval = None

            if fallback_retrieval is not None:
                logger.info("PlanningNode: LLM 路径未产生有效方案，回退到规则生成")
                state.trace.append(TraceEvent(
                    agent=self.name,
                    status="running",
                    message="LLM 生成失败，回退到规则方式生成方案...",
                ))
                fallback_plans = self._fallback_generate(intent, fallback_retrieval)
                # 回退路径：本地化步骤描述
                poi_map = {
                    poi.id: poi
                    for poi in [*fallback_retrieval.activities, *fallback_retrieval.restaurants]
                }
                plans = [
                    _localize_plan(p, intent, None, poi_map)
                    for p in fallback_plans
                ]

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
        preference_adjustments: list[str] | None = None,
    ) -> list[PlanSchema]:
        """调用 LLM 生成方案选择，然后组装 PlanSchema。失败时返回空列表。"""
        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_build_user_message(
                    intent, retrieval, rejection_reason, preference_adjustments
                ),
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
    # 多策略并行规划路径
    # ------------------------------------------------------------------

    async def _call_llm_single_plan(
        self,
        intent: UserIntentSchema,
        retrieval_result: RetrievalResult,
        rejection_reason: str | None = None,
        preference_adjustments: list[str] | None = None,
    ) -> list[PlanSchema]:
        """针对单个 RetrievalResult（含 style）调用 LLM，要求只生成 1 个最优方案。

        失败时返回空列表，不抛出异常，由调用方聚合结果。
        """
        style = retrieval_result.style
        messages = [
            LLMMessage(role="system", content=_SINGLE_PLAN_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=_build_user_message_single(
                    intent, retrieval_result, style,
                    rejection_reason, preference_adjustments,
                ),
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
            logger.warning("PlanningNode: 策略 %r 的 LLM 调用失败: %s", style, exc)
            return []

        try:
            llm_data = parse_json_response(response, required_fields=_REQUIRED_FIELDS)
        except LLMParseError as exc:
            logger.warning(
                "PlanningNode: 策略 %r 的 LLM 响应解析失败: %s | raw=%r",
                style, exc, exc.raw_content[:200],
            )
            return []

        poi_map = _build_poi_map(retrieval_result)
        plans = _plans_from_llm_response(llm_data, intent, retrieval_result, poi_map)

        if not plans:
            logger.warning("PlanningNode: 策略 %r 的 LLM 返回数据未能产生有效方案", style)

        return plans

    async def _plan_from_strategies(
        self,
        intent: UserIntentSchema,
        retrieval_strategies: list[RetrievalResult],
        rejection_reason: str | None = None,
        preference_adjustments: list[str] | None = None,
    ) -> list[PlanSchema]:
        """并行对每个搜索策略调用 LLM，各自生成 1 个方案，合并为候选列表。

        每个策略的方案 ID 包含策略序号（plan_s0_1、plan_s1_1、plan_s2_1），
        保证跨策略 ID 全局唯一，同时允许 _plan_from_strategies 在重试时
        通过 ID 前缀将 rejection reason 精确路由回对应策略（Bug 4 修复）。
        """
        tasks = [
            self._call_llm_single_plan(
                intent,
                strategy,
                self._filter_rejection_reason_for_strategy(
                    rejection_reason, strategy_idx
                ),
                preference_adjustments,
            )
            for strategy_idx, strategy in enumerate(retrieval_strategies)
        ]
        results_per_strategy: list[list[PlanSchema] | BaseException] = (
            await asyncio.gather(*tasks, return_exceptions=True)
        )

        plans: list[PlanSchema] = []
        for strategy_idx, result in enumerate(results_per_strategy):
            if isinstance(result, BaseException):
                logger.warning(
                    "PlanningNode: 策略 %r 的并行调用抛出未捕获异常，跳过: %s",
                    retrieval_strategies[strategy_idx].style,
                    result,
                )
                continue
            for local_idx, plan in enumerate(result, start=1):
                # 赋予含策略序号的 ID，使跨策略计划 ID 全局唯一
                strategy_scoped_id = f"plan_s{strategy_idx}_{local_idx}"
                plans.append(plan.model_copy(update={"id": strategy_scoped_id}))

        return plans

    @staticmethod
    def _filter_rejection_reason_for_strategy(
        rejection_reason: str | None,
        strategy_idx: int,
    ) -> str | None:
        """从全局 rejection_reason 字符串中过滤出属于指定策略的行。

        每行格式为"方案 plan_sN_M（...）：..."，只保留 N == strategy_idx 的行。
        若过滤后无内容，返回 None（不向该策略传递不相关的拒绝原因）。
        """
        if not rejection_reason:
            return None

        prefix = f"plan_s{strategy_idx}_"
        relevant_lines = [
            line for line in rejection_reason.splitlines()
            if prefix in line
        ]
        return "\n".join(relevant_lines) if relevant_lines else None

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
