"""
VerifierNode — 两阶段校验已生成的候选方案，决定是否通过。

第一阶段（硬约束，代码直接 reject）：
  1. 总时长超用户上限 → 直接 reject
  2. 距离超用户上限 → 直接 reject

第二阶段（LLM Critic，llm_client 不为 None 时执行）：
  将以下内容喂给 LLM：
  - 用户完整意图（原始需求、场景、参与人员、饮食要求、软性偏好）
  - 方案完整详情（每个步骤的 POI 名称/类别/评分/距离/营业时间/价格/排队时间）
  - 代码规则检查结果（营业时间覆盖、audience_fit 匹配、rating 数值）作为参考信息
  - 所有候选方案列表（用于方案间差异度评估）
  LLM 对每个方案从 7 个维度各打 1-5 分：
    1. 风格一致性
    2. 人群真实匹配
    3. 节奏合理性
    4. 需求覆盖度
    5. 可执行性
    6. 方案差异度
    7. 整体体验感
  7 个维度平均分 < 3.0 → reject，附带改进建议传给 PlanningNode 下一轮参考。

构造函数参数：
  llm_client: LLMClient | None
    - 不为 None → 执行两阶段校验
    - 为 None → 退化为纯代码校验（仅第一阶段硬约束）

复用策略：
  第二阶段的 _is_open_for_window / _matches_audience 不再单独 reject，
  而是收集为结构化数据作为"参考信息"传给 LLM。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.schemas.planning import PlanSchema, POISchema, UserIntentSchema

from app.services.activity_workflow import (
    _is_open_for_window,
    _matches_audience,
)
from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, TraceEvent
from llm.base import LLMClient, LLMError, LLMMessage
from llm.structured_output import LLMParseError, parse_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM Critic prompt
# ---------------------------------------------------------------------------

_CRITIC_SYSTEM_PROMPT = """\
你是一位严格的本地生活行程方案审核专家。你的任务是对候选行程方案进行质量评估。

请对每个方案从以下 7 个维度各打 1-5 分（整数），并给出一句话说明：
1. 风格一致性：活动+餐厅组合是否连贯、与策略风格是否匹配
2. 人群真实匹配：语义层面的适配（5岁孩子能否参与、减脂与餐厅菜式是否契合）
3. 节奏合理性：时间分配是否合理，活动强度前后搭配是否舒适
4. 需求覆盖度：soft_preferences 和 diet_requirements 被满足的程度
5. 可执行性：综合排队时间、预约需求判断方案是否能顺利走完
6. 方案差异度：与其他候选方案相比是否提供真正不同的选择
7. 整体体验感：用户跑完这个方案会不会觉得满意

评分标准：
1 = 很差，2 = 较差，3 = 一般，4 = 较好，5 = 优秀

输出必须是合法 JSON，格式如下：
{
  "evaluations": [
    {
      "plan_id": "方案id",
      "scores": {
        "style_consistency": 4,
        "audience_match": 3,
        "rhythm": 4,
        "requirement_coverage": 3,
        "feasibility": 4,
        "differentiation": 3,
        "overall_experience": 4
      },
      "comments": {
        "style_consistency": "一句话说明",
        "audience_match": "一句话说明",
        "rhythm": "一句话说明",
        "requirement_coverage": "一句话说明",
        "feasibility": "一句话说明",
        "differentiation": "一句话说明",
        "overall_experience": "一句话说明"
      },
      "improvement_suggestion": "若平均分低于3.0，给出改进建议；否则留空字符串"
    }
  ]
}
"""

_SCORE_KEYS = [
    "style_consistency",
    "audience_match",
    "rhythm",
    "requirement_coverage",
    "feasibility",
    "differentiation",
    "overall_experience",
]

_LLM_PASS_THRESHOLD = 3.0


# ---------------------------------------------------------------------------
# Prompt 构建
# ---------------------------------------------------------------------------

def _build_critic_user_message(
    intent: UserIntentSchema,
    plans: list[PlanSchema],
    code_checks: dict[str, list[dict[str, Any]]],
) -> str:
    """构建发送给 LLM Critic 的用户消息。

    Args:
        intent: 用户完整意图
        plans: 待评估的候选方案列表
        code_checks: plan_id -> 规则检查问题列表（每条含 rule/poi_name/detail）
    """
    parts: list[str] = []

    # --- 用户意图 ---
    parts.append("=== 用户意图 ===\n")
    parts.append(f"原始需求：{intent.raw_text}\n")
    parts.append(f"场景：{intent.scenario}\n")
    tw = intent.time_window
    parts.append(f"出行时间：{tw.date} {tw.start or ''}–{tw.end or ''} {tw.label or ''}\n".strip() + "\n")
    parts.append(f"出行时长：{intent.duration_hours_min}–{intent.duration_hours_max} 小时\n")

    # 参与人员
    participant_parts = []
    for p in intent.participants:
        desc = f"{p.type}×{p.count}"
        if p.age is not None:
            desc += f"（{p.age}岁）"
        if p.notes:
            desc += f"[{', '.join(p.notes)}]"
        participant_parts.append(desc)
    parts.append(f"参与人员：{', '.join(participant_parts)}\n")

    if intent.diet_requirements:
        parts.append(f"饮食要求：{', '.join(intent.diet_requirements)}\n")
    if intent.soft_preferences:
        parts.append(f"软性偏好：{', '.join(intent.soft_preferences)}\n")
    if intent.hard_constraints:
        parts.append(f"硬性约束：{', '.join(intent.hard_constraints)}\n")
    parts.append("\n")

    # --- 候选方案详情 ---
    parts.append("=== 候选方案详情 ===\n")
    for plan in plans:
        parts.append(f"--- 方案 {plan.id}：{plan.title} ---\n")
        parts.append(f"摘要：{plan.summary}\n")
        parts.append(f"总时长：{plan.total_duration_minutes} 分钟\n")
        parts.append(f"预估费用：{plan.estimated_cost_min}–{plan.estimated_cost_max} 元/人\n")

        # POI 详情
        poi_map = {poi.id: poi for poi in plan.pois}
        parts.append("包含地点：\n")
        for poi in plan.pois:
            af = poi.audience_fit
            parts.append(
                f"  - {poi.name}（{poi.subcategory}）\n"
                f"    评分: {poi.rating}/5 | 距离: {poi.distance_km}km | "
                f"营业: {poi.business_hours.open}–{poi.business_hours.close}\n"
                f"    人均: {poi.price_per_person}元 | 排队: {poi.queue.wait_minutes}分钟 "
                f"（{poi.queue.level}）| 可预约: {'是' if poi.reservable else '否'}\n"
                f"    受众适配: 家庭={af.family} 5岁儿童={af.child_age_5} "
                f"减脂={af.weight_loss_friendly} 朋友群={af.friends_group}\n"
            )

        # 步骤时序
        parts.append("行程步骤：\n")
        for step in plan.steps:
            parts.append(
                f"  {step.start_time}–{step.end_time} [{step.type}] {step.title}\n"
            )

        # 代码规则检查结果（作为参考信息，不是 reject 依据）
        checks = code_checks.get(plan.id, [])
        if checks:
            parts.append("代码规则检查发现的问题（仅供参考）：\n")
            for c in checks:
                parts.append(f"  - [{c.get('rule', '')}] {c.get('detail', '')}\n")
        else:
            parts.append("代码规则检查：无问题\n")

        parts.append("\n")

    parts.append(
        "请对以上每个方案按照系统 prompt 要求的格式进行评分，以 JSON 格式返回。\n"
    )
    return "".join(parts)


# ---------------------------------------------------------------------------
# 规则检查（收集，不 reject）
# ---------------------------------------------------------------------------

def _collect_rule_checks(
    intent: UserIntentSchema,
    plan: PlanSchema,
) -> list[dict[str, Any]]:
    """收集第二阶段参考信息：营业时间、audience_fit、rating 问题。

    不再单独 reject，只作为结构化数据传给 LLM。
    """
    issues: list[dict[str, Any]] = []

    for poi in plan.pois:
        if not _is_open_for_window(poi, intent):
            issues.append({
                "rule": "business_hours",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} 营业时间 {poi.business_hours.open}–{poi.business_hours.close} "
                    f"不完全覆盖用户时间窗口 "
                    f"{intent.time_window.start}–{intent.time_window.end}"
                ),
            })

        if not _matches_audience(intent, poi):
            issues.append({
                "rule": "audience_fit",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} audience_fit 对 scenario={intent.scenario} 适配度可能不足"
                ),
            })

        _RATING_THRESHOLD = 2.5
        if 0 < poi.rating < _RATING_THRESHOLD:
            issues.append({
                "rule": "low_rating",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} 评分 {poi.rating}/5 低于参考门槛 {_RATING_THRESHOLD}"
                ),
            })

    return issues


# ---------------------------------------------------------------------------
# 硬约束检查（第一阶段，直接 reject）
# ---------------------------------------------------------------------------

def _check_hard_constraints(
    intent: UserIntentSchema,
    plan: PlanSchema,
) -> list[dict[str, Any]]:
    """只检查时长和距离两条硬约束，返回违规列表（空 = 通过）。"""
    violations: list[dict[str, Any]] = []

    max_allowed_minutes = int(intent.duration_hours_max * 60)
    if plan.total_duration_minutes > max_allowed_minutes:
        violations.append({
            "rule": "duration",
            "detail": (
                f"方案总时长 {plan.total_duration_minutes} 分钟 "
                f"超过用户上限 {max_allowed_minutes} 分钟"
            ),
        })

    for poi in plan.pois:
        if poi.distance_km > intent.max_distance_km:
            violations.append({
                "rule": "distance",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} 距离 {poi.distance_km} km "
                    f"超过用户上限 {intent.max_distance_km} km"
                ),
            })

    return violations


# ---------------------------------------------------------------------------
# VerifierNode
# ---------------------------------------------------------------------------

class VerifierNode(BaseNode):
    """两阶段校验节点。

    第一阶段（硬约束）：时长超限或距离超限直接 reject，不走 LLM。
    第二阶段（LLM Critic）：通过硬约束的方案送给 LLM 打分，平均分 < 3.0 则 reject。

    llm_client 为 None 时退化为纯代码校验（仅第一阶段）。
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client

    @property
    def name(self) -> str:
        return "verifier_node"

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="开始两阶段方案校验（硬约束 + LLM Critic）...",
        ))

        intent = state.intent
        if intent is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message="state.intent 为空，无法校验方案",
            ))
            logger.error("[%s] state.intent is None, cannot verify plans", self.name)
            return state

        if not state.candidate_plans:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message="没有候选方案，跳过校验",
            ))
            return state

        # ------------------------------------------------------------------
        # 第一阶段：硬约束（时长 + 距离）
        # ------------------------------------------------------------------
        hard_rejection_batch: list[dict[str, Any]] = []

        for plan in state.candidate_plans:
            violations = _check_hard_constraints(intent, plan)
            if violations:
                hard_rejection_batch.append({
                    "plan_id": plan.id,
                    "plan_title": plan.title,
                    "violations": violations,
                    "stage": "hard_constraint",
                })

        if hard_rejection_batch:
            failed_ids = {r["plan_id"] for r in hard_rejection_batch}
            state.candidate_plans = [
                p for p in state.candidate_plans if p.id not in failed_ids
            ]
            state.plan_revision_count += 1
            state.verifier_rejection_reasons.extend(hard_rejection_batch)

            state.trace.append(TraceEvent(
                agent=self.name,
                status="running",
                message=(
                    f"硬约束校验：{len(hard_rejection_batch)} 个方案违反时长/距离约束已移除，"
                    f"剩余 {len(state.candidate_plans)} 个方案继续进入 LLM 评审"
                ),
            ))
            logger.warning(
                "[%s] Phase 1: %d plans failed hard constraints and were removed: %s",
                self.name,
                len(hard_rejection_batch),
                sorted(failed_ids),
            )
        else:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="running",
                message=f"硬约束校验通过，{len(state.candidate_plans)} 个方案进入 LLM 评审",
            ))

        # 如果硬约束已经把所有方案都 reject，直接结束
        if not state.candidate_plans:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message="所有方案均被硬约束拒绝，跳过 LLM 评审",
            ))
            return state

        # ------------------------------------------------------------------
        # 第二阶段：LLM Critic（仅 llm_client 不为 None 时执行）
        # ------------------------------------------------------------------
        if self._llm is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message=(
                    f"LLM Critic 已跳过（llm_client=None），"
                    f"剩余 {len(state.candidate_plans)} 个方案通过校验"
                ),
            ))
            logger.info(
                "[%s] LLM Critic skipped (no llm_client), %d plans passed",
                self.name,
                len(state.candidate_plans),
            )
            return state

        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message=f"正在对 {len(state.candidate_plans)} 个方案进行 LLM 多维度评审...",
        ))

        llm_rejection_batch = await self._run_llm_critic(intent, state.candidate_plans)

        if llm_rejection_batch:
            failed_ids = {r["plan_id"] for r in llm_rejection_batch}
            state.candidate_plans = [
                p for p in state.candidate_plans if p.id not in failed_ids
            ]
            state.plan_revision_count += 1
            state.verifier_rejection_reasons.extend(llm_rejection_batch)

            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message=(
                    f"LLM Critic：{len(llm_rejection_batch)} 个方案平均分 < {_LLM_PASS_THRESHOLD} 已移除，"
                    f"剩余 {len(state.candidate_plans)} 个方案，"
                    f"revision_count={state.plan_revision_count}"
                ),
            ))
            logger.warning(
                "[%s] Phase 2: %d plans failed LLM critic (avg score < %.1f): %s",
                self.name,
                len(llm_rejection_batch),
                _LLM_PASS_THRESHOLD,
                sorted(failed_ids),
            )
        else:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message=(
                    f"LLM Critic 通过：全部 {len(state.candidate_plans)} 个方案质量达标"
                ),
            ))
            logger.info(
                "[%s] Phase 2: all %d plans passed LLM critic",
                self.name,
                len(state.candidate_plans),
            )

        return state

    # ------------------------------------------------------------------
    # LLM Critic 调用
    # ------------------------------------------------------------------

    async def _run_llm_critic(
        self,
        intent: UserIntentSchema,
        plans: list[PlanSchema],
    ) -> list[dict[str, Any]]:
        """调用 LLM 对所有方案进行多维度评分。

        返回被 reject 的方案列表（格式同硬约束 rejection_batch）。
        LLM 调用或解析失败时静默降级，返回空列表（不 reject）。
        """
        # 收集每个方案的代码规则检查结果，作为 LLM 的参考信息
        code_checks: dict[str, list[dict[str, Any]]] = {
            plan.id: _collect_rule_checks(intent, plan)
            for plan in plans
        }

        user_message = _build_critic_user_message(intent, plans, code_checks)

        messages = [
            LLMMessage(role="system", content=_CRITIC_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_message),
        ]

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._llm.chat(
                    messages,
                    temperature=0.3,
                    max_tokens=2048,
                    json_mode=True,
                ),
            )
        except LLMError as exc:
            logger.warning(
                "[%s] LLM Critic 调用失败，跳过第二阶段校验: %s",
                self.name, exc,
            )
            return []

        try:
            llm_data = parse_json_response(response, required_fields=["evaluations"])
        except LLMParseError as exc:
            logger.warning(
                "[%s] LLM Critic 响应解析失败，跳过第二阶段校验: %s | raw=%r",
                self.name, exc, exc.raw_content[:200],
            )
            return []

        return self._extract_rejections(llm_data, plans)

    def _extract_rejections(
        self,
        llm_data: dict[str, Any],
        plans: list[PlanSchema],
    ) -> list[dict[str, Any]]:
        """从 LLM 评分结果中提取低分（平均分 < 3.0）的方案为 rejection 记录。"""
        evaluations: list[dict[str, Any]] = llm_data.get("evaluations", [])
        if not isinstance(evaluations, list):
            logger.warning("[%s] LLM 返回的 evaluations 不是列表，跳过", self.name)
            return []

        plan_id_set = {p.id for p in plans}
        plan_title_map = {p.id: p.title for p in plans}

        rejections: list[dict[str, Any]] = []

        for eval_item in evaluations:
            plan_id = eval_item.get("plan_id", "")
            if plan_id not in plan_id_set:
                logger.warning(
                    "[%s] LLM 返回了未知 plan_id=%r，忽略", self.name, plan_id
                )
                continue

            scores_raw = eval_item.get("scores", {})
            if not isinstance(scores_raw, dict):
                continue

            score_values: list[float] = []
            for key in _SCORE_KEYS:
                val = scores_raw.get(key)
                try:
                    score_values.append(float(val))
                except (TypeError, ValueError):
                    logger.warning(
                        "[%s] 方案 %s 的维度 %s 分值无效: %r，跳过该维度",
                        self.name, plan_id, key, val,
                    )

            if not score_values:
                logger.warning(
                    "[%s] 方案 %s 无有效评分，跳过 LLM reject 判定", self.name, plan_id
                )
                continue

            avg_score = sum(score_values) / len(score_values)

            if avg_score < _LLM_PASS_THRESHOLD:
                improvement = eval_item.get("improvement_suggestion", "")
                comments = eval_item.get("comments", {})

                detail_parts = [
                    f"LLM 多维度平均分 {avg_score:.2f} < {_LLM_PASS_THRESHOLD}"
                ]
                for key in _SCORE_KEYS:
                    s = scores_raw.get(key, "?")
                    comment = comments.get(key, "") if isinstance(comments, dict) else ""
                    detail_parts.append(f"  {key}={s}: {comment}")
                if improvement:
                    detail_parts.append(f"改进建议: {improvement}")

                rejections.append({
                    "plan_id": plan_id,
                    "plan_title": plan_title_map.get(plan_id, ""),
                    "stage": "llm_critic",
                    "avg_score": round(avg_score, 2),
                    "violations": [
                        {
                            "rule": "llm_critic_low_score",
                            "detail": "\n".join(detail_parts),
                        }
                    ],
                    "improvement_suggestion": improvement,
                })
                logger.info(
                    "[%s] 方案 %s 平均分 %.2f < %.1f，建议: %r",
                    self.name, plan_id, avg_score, _LLM_PASS_THRESHOLD,
                    improvement[:80] if improvement else "",
                )
            else:
                logger.info(
                    "[%s] 方案 %s 平均分 %.2f >= %.1f，通过 LLM Critic",
                    self.name, plan_id, avg_score, _LLM_PASS_THRESHOLD,
                )

        return rejections
