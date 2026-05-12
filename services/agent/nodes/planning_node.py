"""
PlanningNode — LLM 驱动的行程方案生成节点。

新架构：
  PlanningNode 是"玩家"（选择路线方），RetrievalNode 是"资源方"（提供候选）。
  PlanningNode 驱动多跳探索循环，每跳调用 RetrievalNode.search_and_judge() 获取候选，
  然后由 LLM 决定：pick_poi / search_meal / stop。

核心流程：
1. 从 state 读取风格方向（style_hints）和天气
2. 3 个风格并行执行 _explore_one_style()，每个探索一条 POI 序列
3. 每个探索循环内：搜索候选 -> LLM 决策 -> 更新位置 -> 继续或结束
4. 每个探索结果组装为 PlanSchema
5. 失败时回退到规则生成

节点约束：
- 继承 BaseNode，通过构造函数接收 LLMClient 和 RetrievalNode 引用
- 向 state.trace 追加 TraceEvent
- 不直接访问数据库或 HTTP
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from agent.nodes.base import BaseNode
from agent.nodes.retrieval_node import RetrievalNode
from agent.state.types import PlanningState, RetrievalResult, TraceEvent
from app.schemas.planning import ItineraryStepSchema, PlanSchema, POISchema, UserIntentSchema
from app.services.activity_workflow import (
    ConstraintCheckResult,
    _build_plan_from_steps,
    generate_actions,
    generate_plans,
)
from domain.route import haversine_km, to_travel_minutes
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
时长约束：活动类建议 45-120 分钟，餐厅类建议 40-80 分钟。\
确保所有地点时长之和加上出行时间（约 10-20 分钟）不超过时间窗口总长。\
如果时间窗口有剩余（>= 30 分钟），优先增加一个活动地点，而不是让时间空着。
5. 活动数量根据时间窗口决定：
   - 总时长 >= 6 小时：至少 2 个活动
   - 总时长 >= 8 小时：至少 3 个活动
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
时长约束：活动类建议 45-120 分钟，餐厅类建议 40-80 分钟。\
确保所有地点时长之和加上出行时间（约 10-20 分钟）不超过时间窗口总长。\
如果时间窗口有剩余（>= 30 分钟），优先增加一个活动地点，而不是让时间空着。
4. 活动数量根据时间窗口决定：
   - 总时长 >= 6 小时：至少 2 个活动
   - 总时长 >= 8 小时：至少 3 个活动
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

# ---------------------------------------------------------------------------
# Hop Decision Prompt — PlanningNode 驱动多跳探索时使用
# ---------------------------------------------------------------------------

_HOP_DECISION_SYSTEM_PROMPT = """\
你是一个行程路线规划师，负责为用户规划一条 spatially coherent 的路线。

=== 你的角色 ===
你是"玩家"——从当前位置附近的候选 POI 中选择下一站，决定何时用餐，何时结束。
你的核心目标是：尽量用满剩余时间，为用户构建一条 3-4 个站点的充实路线。

=== 决策类型 ===
1. pick_poi — 从当前候选列表中选择一个 POI 作为下一站
   输出时使用 selected_poi_index (1-based 序号) 指定选中的候选
2. search_meal — 想吃东西了，切换到餐厅搜索（每段行程最多用餐一次）
3. stop — 仅在以下情况停止：
   * 候选列表为空
   * 剩余时间不足 30 分钟
   * 已选 4 个以上 POI 且行程已经很充实
   * 当前所有候选评分都低于 3.0

=== 选中的规则 ===
- 优先选择评分高（>=3.5）、适合当前场景和人群的 POI
- 注意剩余时间：地点游玩时间+出行时间不能超出剩余可用时间
- 行程紧凑比松散更好：优先选择距离当前位置近的 POI
- 路线应有逻辑：从近到远或沿同一方向推进，不要来回折返
- 除非候选真的很差（全部 < 3.0 分），否则不要提前 stop——尽量继续探索
- 出发后的前两跳不应 stop，除非候选真的不合适

输出格式（JSON）：
{
  "action": "pick_poi | search_meal | stop",
  "selected_poi_index": <int, pick_poi 时填写候选序号 1-based>,
  "reasoning": "<决策理由，一句话>"
}
"""

# ---------------------------------------------------------------------------
# POI 序列化
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ["plans"]


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
            f"  营业时间: {poi.business_hours.open}-{poi.business_hours.close}\n"
            f"  人均费用: {poi.price_per_person} 元\n"
            f"  当前等位: {poi.queue.wait_minutes} 分钟\n"
            f"  可预约: {'是' if poi.reservable else '否'}\n"
        )
    return "".join(lines)


def _format_time_window(intent: UserIntentSchema) -> str:
    """将时间窗口格式化为可读字符串。"""
    tw = intent.time_window
    if tw.start is not None and tw.end is not None:
        return f"{tw.date} {tw.start}-{tw.end}"

    if tw.label:
        return f"{tw.date} {tw.label}"
    return f"{tw.date}（约 {intent.duration_hours_min}-{intent.duration_hours_max} 小时）"


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
        f"出行时长：{intent.duration_hours_min}-{intent.duration_hours_max} 小时\n"
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
    """构建单策略 LLM 调用的用户消息，包含风格说明。"""
    parts: list[str] = []

    parts.append(
        f"用户需求：{intent.raw_text}\n"
        f"场景：{intent.scenario}\n"
        f"出行时间：{_format_time_window(intent)}\n"
        f"出行时长：{intent.duration_hours_min}-{intent.duration_hours_max} 小时\n"
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
# Hop decision 上下文构建
# ---------------------------------------------------------------------------

def _build_hop_user_message(
    candidates: list[POISchema],
    selected: list[POISchema],
    hop: int,
    remaining_minutes: int,
    cumulative_km: float,
    weather: str,
    current_lat: float,
    current_lng: float,
    origin_lat: float,
    origin_lng: float,
    style: str,
    is_meal_search: bool = False,
) -> str:
    """构建每跳 LLM 决策的用户消息。

    Args:
        candidates:    当前候选 POI 列表。
        selected:      已选 POI 列表。
        hop:           当前跳数（0-based）。
        remaining_minutes: 剩余可用时间（分钟）。
        cumulative_km: 累计里程（km）。
        weather:       天气描述。
        current_lat/lng:  当前位置坐标。
        origin_lat/lng:   出发地坐标。
        style:         当前策略方向。
        is_meal_search: 是否正在搜索餐厅（True 时不显示 search_meal 选项）。

    Returns:
        格式化的用户消息字符串。
    """
    parts: list[str] = []

    # === 上下文信息 ===
    parts.append("=== 当前状态 ===\n")
    parts.append(f"风格：{style}\n")
    parts.append(f"天气：{weather}\n")
    parts.append(f"跳数：第 {hop + 1} 轮\n")
    parts.append(f"剩余时间：约 {remaining_minutes} 分钟\n")
    parts.append(f"累计里程：约 {cumulative_km:.1f}km\n")
    parts.append(f"当前位置：距出发地 {haversine_km(origin_lat, origin_lng, current_lat, current_lng):.1f}km\n")

    if selected:
        parts.append("\n=== 已选 POI ===\n")
        for i, poi in enumerate(selected, 1):
            parts.append(f"  {i}. {poi.name}（{poi.subcategory}）- 游玩 {poi.recommended_duration_minutes} 分钟\n")

    # === 候选列表 ===
    type_label = "餐厅" if is_meal_search else "活动"
    parts.append(f"\n=== 当前位置附近的{type_label}候选（共 {len(candidates)} 个）===\n")
    for i, poi in enumerate(candidates, 1):
        parts.append(
            f"  [{i}] {poi.name}（{poi.subcategory}）\n"
            f"      评分 {poi.rating}/5 | 距当前位置 {poi.distance_km:.1f}km\n"
            f"      推荐游玩 {poi.recommended_duration_minutes} 分钟 | 人均 {poi.price_per_person} 元\n"
            f"      营业 {poi.business_hours.open}-{poi.business_hours.close}\n"
        )

    # === 决策提示 ===
    if is_meal_search:
        parts.append("\n请从以上餐厅候选中选择 1 个作为用餐地点，或选择 stop（不饿/时间不够）。")
    else:
        if remaining_minutes > 60:
            parts.append("\n请从以上候选中选择 1 个作为下一站，或选择 search_meal 切换用餐搜索，或选择 stop 结束行程。")
        else:
            parts.append("\n剩余时间不多，请选择 1 个作为最后一站，或 stop 结束。")

    return "".join(parts)


# ---------------------------------------------------------------------------
# 中文本地化
# ---------------------------------------------------------------------------

def _localize_step(step: ItineraryStepSchema, poi_map: dict[str, POISchema]) -> ItineraryStepSchema:
    """将单个行程步骤中的英文描述替换为中文。"""
    desc = step.description

    desc = re.sub(
        r"estimated queue\s+(\d+)\s+minutes?",
        lambda m: f"预计等位 {m.group(1)} 分钟",
        desc,
        flags=re.IGNORECASE,
    )

    desc = re.sub(
        r"Estimated local travel time based on mock POI data\.?",
        "预计本地出行时间（基于模拟数据）。",
        desc,
        flags=re.IGNORECASE,
    )

    desc = desc.strip()

    return step.model_copy(update={"description": desc})


def _localize_fit_summary(intent: UserIntentSchema, extra_poi: POISchema | None) -> list[str]:
    """生成中文版 fit_summary。"""
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
    """对 _build_plan_from_steps 输出的方案进行中文本地化处理。"""
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
    """构建 id -> POISchema 索引。"""
    return {poi.id: poi for poi in [*retrieval.activities, *retrieval.restaurants]}


def _find_poi_in_list(poi_id: str, candidates: list[POISchema]) -> POISchema | None:
    """从列表中查找指定 id 的 POI。"""
    for poi in candidates:
        if poi.id == poi_id:
            return poi
    return None


def _plans_from_llm_response(
    llm_data: dict[str, Any],
    intent: UserIntentSchema,
    retrieval: RetrievalResult,
    poi_map: dict[str, POISchema],
) -> list[PlanSchema]:
    """根据 LLM 返回的 steps 列表方案结果，组装完整的 PlanSchema 列表。"""
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

        plan_title = raw.get("plan_title", "")
        plan_summary = raw.get("plan_summary", "")
        if isinstance(plan_title, str) and plan_title.strip():
            plan = plan.model_copy(update={"title": plan_title.strip()})
        if isinstance(plan_summary, str) and plan_summary.strip():
            plan = plan.model_copy(update={"summary": plan_summary.strip()})

        plan = _localize_plan(plan, intent, None, poi_map)

        plans.append(plan)

    return plans


def _build_plan_from_selected(
    selected: list[POISchema],
    intent: UserIntentSchema,
    style: str,
    index: int,
) -> PlanSchema | None:
    """将探索循环选中的 POI 列表组装为 PlanSchema。

    Args:
        selected: 按顺序选中的 POI 列表。
        intent:   用户规划意图。
        style:    策略方向。
        index:    方案序号（1-based）。

    Returns:
        PlanSchema，或 None（selected 为空时）。
    """
    if not selected:
        return None

    # 估算合理的单 POI 时长：总预算均匀分配，但不超过推荐时长
    total_budget = int(intent.duration_hours_max * 60)
    transit_overhead = len(selected) * 8  # 每段交通约 8 分钟
    activity_budget = max(60, total_budget - transit_overhead)
    per_poi_duration = activity_budget // len(selected)

    steps_spec: list[dict] = []
    has_meal = False
    for poi in selected:
        step_type = "activity"
        if poi.category == "restaurant":
            step_type = "meal"
            has_meal = True
        duration = min(per_poi_duration, poi.recommended_duration_minutes)
        steps_spec.append({
            "poi": poi,
            "type": step_type,
            "duration_minutes": duration,
            "description": None,
        })

    plan = _build_plan_from_steps(intent, steps_spec, index)

    # 覆盖标题和摘要
    if style:
        plan = plan.model_copy(update={"title": f"{style}方案: {plan.title}"})

    # 本地化
    poi_map = {poi.id: poi for poi in selected}
    plan = _localize_plan(plan, intent, None, poi_map)

    return plan


# ---------------------------------------------------------------------------
# PlanningNode
# ---------------------------------------------------------------------------

class PlanningNode(BaseNode):
    """
    Planning Node — LLM 驱动的行程方案生成节点。

    新架构：
    - 通过 _explore_one_style() 驱动多跳探索
    - 每跳调用 retrieval_node.search_and_judge() 获取候选
    - 通过 _llm_hop_decision() 让 LLM 决定下一站动作
    - 3 个风格方向并行探索

    输入（从 state 读取）：
      - state.style_hints: list[str]（3 个策略方向）
      - state.retrieval.weather: str（天气）
      - state.intent: UserIntentSchema（用户约束）
      - state.verifier_rejection_reason: str | None（上一轮被拒绝的原因）
      - state.preference_adjustments: list[str]（用户偏好调整指令）

    输出（写入 state）：
      - state.candidate_plans: list[PlanSchema]（候选方案，含 actions）
      - state.trace: 追加 running / done / error TraceEvent

    依赖：
      - llm_client: LLMClient（用于 hop 决策和方案组装）
      - retrieval_node: RetrievalNode（用于 search_and_judge）
    """

    def __init__(self, llm_client: LLMClient, retrieval_node: RetrievalNode) -> None:
        self._llm = llm_client
        self._retrieval_node = retrieval_node

    @property
    def name(self) -> str:
        return "planning_node"

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="开始探索路线并生成行程方案...",
        ))

        intent = state.intent
        if intent is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message="缺少必要输入：intent 为空，无法生成方案",
            ))
            return state

        weather = state.retrieval.weather if state.retrieval else ""
        style_hints = state.style_hints

        rejection_reason = state.verifier_rejection_reason
        preference_adjustments = state.preference_adjustments or None

        if self._llm is not None and style_hints:
            # 新架构：PlanningNode 驱动探索
            plans = await self._plan_with_exploration(
                intent, weather, style_hints,
                rejection_reason, preference_adjustments,
                traces=traces,
            )
        else:
            # LLM 不可用或无风格方向时回退
            if style_hints:
                logger.info("PlanningNode: LLM 不可用，使用规则降级")
            else:
                logger.info("PlanningNode: 无风格方向，使用规则降级")

            plans = await self._plan_with_fallback(intent, state)

        if not plans:
            logger.info("PlanningNode: 探索未产生有效方案，回退到规则生成")
            state.trace.append(TraceEvent(
                agent=self.name,
                status="running",
                message="探索失败，回退到规则方式生成方案...",
            ))
            plans = self._fallback_generate(intent, state)

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
    # 新架构：探索驱动规划
    # ------------------------------------------------------------------

    async def _plan_with_exploration(
        self,
        intent: UserIntentSchema,
        weather: str,
        style_hints: list[str],
        rejection_reason: str | None = None,
        preference_adjustments: list[str] | None = None,
        state: PlanningState | None = None,
    ) -> list[PlanSchema]:
        """通过多风格并行探索生成方案。

        为每个风格方向运行 _explore_one_style()，然后将探索结果组装为方案。
        并行探索产生的 trace 按风格顺序依次写入 state.trace，避免交叉混乱。
        """
        # 解析出发地坐标
        origin_lat, origin_lng = await self._retrieval_node.resolve_origin(intent)

        # 并行探索 3 个风格
        explore_tasks = [
            asyncio.create_task(
                self._explore_one_style(intent, origin_lat, origin_lng, style, weather)
            )
            for style in style_hints
        ]
        explore_results = await asyncio.gather(*explore_tasks, return_exceptions=True)

        # 将探索结果组装为方案
        plans: list[PlanSchema] = []
        for idx, result in enumerate(explore_results):
            if isinstance(result, BaseException):
                logger.warning(
                    "PlanningNode: 风格 %r 探索抛出异常: %s",
                    style_hints[idx] if idx < len(style_hints) else "unknown",
                    result,
                )
                continue

            selected: list[POISchema]
            style_traces: list[TraceEvent]
            selected, style_traces = result

            # 按风格顺序写入 trace，避免并行交叉
            if state is not None:
                state.trace.extend(style_traces)

            if not selected:
                logger.debug(
                    "PlanningNode: 风格 %r 探索未选中任何 POI，跳过",
                    style_hints[idx] if idx < len(style_hints) else "unknown",
                )
                continue

            plan = _build_plan_from_selected(
                selected, intent,
                style_hints[idx] if idx < len(style_hints) else "",
                idx + 1,
            )
            if plan is not None:
                # 赋予含策略序号的 ID
                plan = plan.model_copy(update={"id": f"plan_s{idx}_1"})
                plans.append(plan)

        return plans

    async def _explore_one_style(
        self,
        intent: UserIntentSchema,
        origin_lat: float,
        origin_lng: float,
        style: str,
        weather: str,
        max_hops: int = 4,
    ) -> tuple[list[POISchema], list[TraceEvent]]:
        """单个风格的多跳探索循环。

            流程：
            1. 初始化位置为出发地
            2. 每一跳：搜索活动候选 -> LLM 决策
            3. LLM 可选择：pick_poi（选 POI）/ search_meal（切换餐厅搜索）/ stop（停止）
            4. 选中 POI 后更新当前位置、累计时间/里程
            5. 达到 max_hops 或 LLM 决定停止时结束

        Args:
            intent:     用户规划意图。
            origin_lat: 出发地纬度。
            origin_lng: 出发地经度。
            style:      策略方向。
            weather:    天气描述。
            max_hops:   最大探索跳数。

        Returns:
            (按顺序选中的 POI 列表, 该风格探索的 trace 事件列表)
        """
        current_lat, current_lng = origin_lat, origin_lng
        selected: list[POISchema] = []
        consumed_minutes = 0
        cumulative_km = 0.0
        has_eaten = False
        total_budget_minutes = int(intent.duration_hours_max * 60)
        traces: list[TraceEvent] = []

        # 每条风格的 LLM 上下文在各跳之间累积
        messages: list[LLMMessage] = [
            LLMMessage(role="system", content=_HOP_DECISION_SYSTEM_PROMPT),
        ]

        traces.append(TraceEvent(
                agent=self.name,
                status="running",
                message=f"开始「{style}」路线探索 (起点 {origin_lat:.4f},{origin_lng:.4f} 预算 {total_budget_minutes}min)",
            ))

        for hop in range(max_hops):
            remaining = total_budget_minutes - consumed_minutes

            # 剩余时间不足 30 分钟时停止
            if remaining < 30:
                logger.debug(
                    "[%s] explore style=%r: remaining=%d min < 30, stopping",
                    self.name, style, remaining,
                )
                break

            traces.append(TraceEvent(
                    agent=self.name,
                    status="running",
                    message=f"第 {hop+1} 跳 — 剩余 {remaining}min · 累计 {cumulative_km:.1f}km",
                ))

            # --- 获取活动候选 ---
            result = await self._retrieval_node.search_and_judge(
                lat=current_lat,
                lng=current_lng,
                style=style,
                intent=intent,
                search_type="activity",
                exclude_poi_ids={p.id for p in selected},
                traces=traces,
            )

            if not result.candidates:
                logger.debug(
                    "[%s] explore style=%r hop=%d: no activity candidates, stopping",
                    self.name, style, hop,
                )
                break

            # --- LLM 决策 ---
            hop_msg = _build_hop_user_message(
                candidates=result.candidates,
                selected=selected,
                hop=hop,
                remaining_minutes=remaining,
                cumulative_km=cumulative_km,
                weather=weather,
                current_lat=current_lat,
                current_lng=current_lng,
                origin_lat=origin_lat,
                origin_lng=origin_lng,
                style=style,
                is_meal_search=False,
            )
            messages.append(LLMMessage(role="user", content=hop_msg))

            decision = await self._llm_hop_decision(messages)
            if decision is None:
                break

            messages.append(LLMMessage(
                role="assistant", content=str(decision),
            ))

            action = decision.get("action", "stop")

            if action == "stop":
                traces.append(TraceEvent(
                    agent=self.name,
                    status="done",
                    message=f"第 {hop+1} 跳 LLM 决定停止探索",
                ))
                logger.debug(
                    "[%s] explore style=%r: LLM stopped at hop %d",
                    self.name, style, hop,
                )
                break

            if action == "pick_poi":
                # 按序号或 ID 选择 POI
                poi = self._resolve_selected_poi(decision, result.candidates)
                if poi is None:
                    logger.warning(
                        "[%s] explore style=%r hop=%d: LLM selected invalid POI, stopping",
                        self.name, style, hop,
                    )
                    break

                step_km = haversine_km(
                    current_lat, current_lng,
                    poi.location.lat, poi.location.lng,
                )
                travel_min = to_travel_minutes(step_km)
                # 估算时长：取推荐时长的 60%（实际时长由 LLM 排方案时灵活决定）
                estimated_duration = min(poi.recommended_duration_minutes, 90)
                step_total = travel_min + estimated_duration

                # 时间约束检查
                if consumed_minutes + step_total > total_budget_minutes:
                    logger.debug(
                        "[%s] explore style=%r: not enough time for %s, stopping",
                        self.name, style, poi.name,
                    )
                    break

                cumulative_km += step_km
                consumed_minutes += step_total
                selected.append(poi)
                current_lat, current_lng = poi.location.lat, poi.location.lng

                traces.append(TraceEvent(
                    agent=self.name,
                    status="done",
                    message=f"第 {hop+1} 跳 选中「{poi.name}」({poi.subcategory}) 距当前位置 {step_km:.1f}km",
                ))

                if poi.category == "restaurant":
                    has_eaten = True

            elif action == "search_meal":
                if has_eaten:
                    logger.debug(
                        "[%s] explore style=%r: already ate, skipping meal search",
                        self.name, style,
                    )
                    continue

                if not getattr(intent, "include_meal", True):
                    continue

                traces.append(TraceEvent(
                    agent=self.name,
                    status="running",
                    message=f"第 {hop+1} 跳 LLM 请求搜索附近餐厅...",
                ))

                meal_result = await self._retrieval_node.search_and_judge(
                    lat=current_lat,
                    lng=current_lng,
                    style=style,
                    intent=intent,
                    search_type="restaurant",
                    exclude_poi_ids={p.id for p in selected},
                    traces=traces,
                )

                if not meal_result.candidates:
                    logger.debug(
                        "[%s] explore style=%r: no restaurant candidates found",
                        self.name, style,
                    )
                    continue

                # LLM 从餐厅候选中选择
                meal_hop_msg = _build_hop_user_message(
                    candidates=meal_result.candidates,
                    selected=selected,
                    hop=hop,
                    remaining_minutes=remaining,
                    cumulative_km=cumulative_km,
                    weather=weather,
                    current_lat=current_lat,
                    current_lng=current_lng,
                    origin_lat=origin_lat,
                    origin_lng=origin_lng,
                    style=style,
                    is_meal_search=True,
                )
                messages.append(LLMMessage(role="user", content=meal_hop_msg))

                meal_decision = await self._llm_hop_decision(messages)
                if meal_decision is None:
                    continue

                messages.append(LLMMessage(
                    role="assistant", content=str(meal_decision),
                ))

                meal_action = meal_decision.get("action", "stop")
                if meal_action == "pick_poi":
                    restaurant = self._resolve_selected_poi(
                        meal_decision, meal_result.candidates,
                    )
                    if restaurant is not None:
                        step_km = haversine_km(
                            current_lat, current_lng,
                            restaurant.location.lat, restaurant.location.lng,
                        )
                        travel_min = to_travel_minutes(step_km)
                        step_total = travel_min + restaurant.recommended_duration_minutes

                        if consumed_minutes + step_total <= total_budget_minutes:
                            cumulative_km += step_km
                            consumed_minutes += step_total
                            selected.append(restaurant)
                            current_lat = restaurant.location.lat
                            current_lng = restaurant.location.lng
                            has_eaten = True
                            traces.append(TraceEvent(
                                agent=self.name,
                                status="done",
                                message=f"选中「{restaurant.name}」作为用餐点 距当前位置 {step_km:.1f}km",
                            ))

        traces.append(TraceEvent(
            agent=self.name,
            status="done",
            message=f"「{style}」探索完成，共 {len(selected)} 个 POI · 累计 {cumulative_km:.1f}km · 耗时 {consumed_minutes}min",
        ))

        return selected, traces

    def _resolve_selected_poi(
        self,
        decision: dict[str, Any],
        candidates: list[POISchema],
    ) -> POISchema | None:
        """从 LLM 决策中解析选中的 POI。

        支持两种引用方式：
        1. selected_poi_index — 1-based 序号
        2. selected_poi_id — POI 的 id 字段
        """
        idx = decision.get("selected_poi_index")
        if idx is not None:
            try:
                idx_int = int(idx)
                if 1 <= idx_int <= len(candidates):
                    return candidates[idx_int - 1]
            except (TypeError, ValueError):
                pass

        poi_id = decision.get("selected_poi_id")
        if poi_id is not None:
            return _find_poi_in_list(str(poi_id), candidates)

        return None

    async def _llm_hop_decision(
        self,
        messages: list[LLMMessage],
    ) -> dict[str, Any] | None:
        """LLM 决策：从当前候选中选择下一站动作。

        Args:
            messages: 累积的对话消息（会在调用时追加，不修改原列表）。

        Returns:
            {"action": "pick_poi"|"search_meal"|"stop", "selected_poi_index": int, "reasoning": str}
            或 None（调用失败时）。
        """
        loop = asyncio.get_running_loop()

        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._llm.chat(
                    messages,
                    temperature=0.7,
                    max_tokens=512,
                    json_mode=True,
                ),
            )
            parsed = parse_json_response(response, required_fields=["action"])

            action = parsed.get("action", "stop")
            if action not in ("pick_poi", "search_meal", "stop"):
                logger.warning(
                    "[%s] _llm_hop_decision: unknown action=%r, falling back to stop",
                    self.name, action,
                )
                return {"action": "stop", "reasoning": "未知动作，自动停止"}

            return {
                "action": action,
                "selected_poi_index": parsed.get("selected_poi_index"),
                "selected_poi_id": parsed.get("selected_poi_id"),
                "reasoning": parsed.get("reasoning", ""),
            }

        except LLMError as exc:
            logger.warning("[%s] _llm_hop_decision: LLM 调用失败: %s", self.name, exc)
            return None
        except LLMParseError as exc:
            logger.warning(
                "[%s] _llm_hop_decision: LLM 响应解析失败: %s",
                self.name, exc,
            )
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] _llm_hop_decision: 异常: %s", self.name, exc)
            return None

    # ------------------------------------------------------------------
    # 回退路径（LLM 不可用或无风格方向时）
    # ------------------------------------------------------------------

    async def _plan_with_fallback(
        self,
        intent: UserIntentSchema,
        state: PlanningState,
    ) -> list[PlanSchema]:
        """LLM 不可用时的回退方案。

        直接使用 searcher 搜索一次，然后使用规则方式生成方案。
        """
        loop = asyncio.get_running_loop()

        try:
            origin_lat, origin_lng = await self._retrieval_node.resolve_origin(intent)
        except Exception:  # noqa: BLE001
            origin_lat, origin_lng = 31.2304, 121.4737

        # 搜索活动
        try:
            activities = await loop.run_in_executor(
                None,
                lambda: self._retrieval_node.searcher.search_activities(intent),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] fallback: activity search failed: %s", self.name, exc)
            activities = []

        # 搜索餐厅
        try:
            restaurants = await loop.run_in_executor(
                None,
                lambda: self._retrieval_node.searcher.search_restaurants(intent),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("[%s] fallback: restaurant search failed: %s", self.name, exc)
            restaurants = []

        # 营业时间过滤
        checked = ConstraintCheckResult(
            activities=activities,
            restaurants=restaurants,
            rejected=[],
        )

        plans = generate_plans(intent, checked)

        # 本地化
        poi_map = {
            poi.id: poi
            for poi in [*checked.activities, *checked.restaurants]
        }
        plans = [
            _localize_plan(p, intent, None, poi_map)
            for p in plans
        ]

        return plans

    # ------------------------------------------------------------------
    # 规则降级路径（保持向后兼容）
    # ------------------------------------------------------------------

    def _fallback_generate(
        self,
        intent: UserIntentSchema,
        state: PlanningState,
    ) -> list[PlanSchema]:
        """最后的降级方案：从 state.retrieval 或 state.retrieval_strategies 取候选。

        如果没有任何可用候选，返回空列表。
        """
        # 尝试从 state.retrieval_strategies 聚合所有候选
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

            if merged_activities:
                checked = ConstraintCheckResult(
                    activities=merged_activities,
                    restaurants=merged_restaurants,
                    rejected=[],
                )
                return generate_plans(intent, checked)

        # 尝试从 state.retrieval 取 POI
        retrieval = state.retrieval
        if retrieval is not None and (retrieval.activities or retrieval.restaurants):
            checked = ConstraintCheckResult(
                activities=retrieval.activities,
                restaurants=retrieval.restaurants,
                rejected=[],
            )
            return generate_plans(intent, checked)

        return []

    # ------------------------------------------------------------------
    # LLM 路径（保留用于外部调用/向后兼容）
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
