"""
VerifierNode — 规则校验已生成的候选方案，决定是否通过。

校验规则（按顺序，全部通过才放行）：
  1. 时间合法性   — 方案总时长不超过 intent.duration_hours_max
  2. 距离约束     — 所有 POI 的 distance_km 在 intent.max_distance_km 以内
  3. 营业时间     — 所有 POI 在用户时间窗口内营业（复用 _is_open_for_window）
  4. 受众适配     — 所有 POI 的 audience_fit 满足 scenario 要求（复用 _matches_audience）
  5. 评分门槛     — 所有 POI 的 rating 不低于 2.5（rating == 0 表示无评分数据，跳过检查）

输出行为：
  - 全部通过：state.verifier_rejection_reasons 保持不变，返回 state
  - 有问题：记录每个失败方案的拒绝原因，将失败方案从 state.candidate_plans 过滤掉，
            state.plan_revision_count += 1，state.verifier_rejection_reasons 追加本次结果
            （供 Planning Node 参考）。若所有方案均失败，candidate_plans 变为空列表，
            Orchestrator 检测到 plan_revision_count 增加后可触发 Planning Node 重新生成。

复用策略：
  直接从 activity_workflow 模块 import _matches_audience、_is_open_for_window，
  不重新实现，保持逻辑单一来源。
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.planning import PlanSchema, POISchema, UserIntentSchema

# 直接复用 activity_workflow 里的校验函数，不重写
from app.services.activity_workflow import (
    _is_open_for_window,
    _matches_audience,
)
from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, TraceEvent

logger = logging.getLogger(__name__)


class VerifierNode(BaseNode):
    """规则校验节点：校验 state.candidate_plans 中每个方案是否满足约束。

    全部通过则不修改 plan_revision_count；有失败则：
      1. 把失败方案从 state.candidate_plans 中过滤掉，只保留通过的方案
      2. plan_revision_count += 1
      3. 将拒绝原因写入 state.verifier_rejection_reasons 以便 Planning Node 重试
    """

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="开始校验候选方案的时间、距离、营业时间、受众适配和 POI 评分...",
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

        rejection_batch: list[dict[str, Any]] = []

        for plan in state.candidate_plans:
            plan_rejections = _verify_plan(intent, plan)
            if plan_rejections:
                rejection_batch.append({
                    "plan_id": plan.id,
                    "plan_title": plan.title,
                    "violations": plan_rejections,
                })

        if rejection_batch:
            failed_ids = {r["plan_id"] for r in rejection_batch}
            state.candidate_plans = [p for p in state.candidate_plans if p.id not in failed_ids]

            state.plan_revision_count += 1
            state.verifier_rejection_reasons.extend(rejection_batch)

            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message=(
                    f"校验未通过：{len(rejection_batch)} 个方案有违规已移除，"
                    f"剩余 {len(state.candidate_plans)} 个方案，"
                    f"plan_ids={sorted(failed_ids)}，revision_count={state.plan_revision_count}"
                ),
            ))
            logger.warning(
                "[%s] %d plans failed verification and were removed (revision_count=%d): %s",
                self.name,
                len(rejection_batch),
                state.plan_revision_count,
                sorted(failed_ids),
            )
        else:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message=f"全部 {len(state.candidate_plans)} 个方案通过校验",
            ))
            logger.info(
                "[%s] all %d plans passed verification", self.name, len(state.candidate_plans)
            )

        return state


# ---------------------------------------------------------------------------
# 内部校验逻辑
# ---------------------------------------------------------------------------

def _verify_plan(intent: UserIntentSchema, plan: PlanSchema) -> list[dict[str, Any]]:
    """对单个方案运行全部校验规则，返回违规列表（空列表表示通过）。"""
    violations: list[dict[str, Any]] = []

    # 规则 1：时间合法性
    max_allowed_minutes = int(intent.duration_hours_max * 60)
    if plan.total_duration_minutes > max_allowed_minutes:
        violations.append({
            "rule": "duration",
            "detail": (
                f"方案总时长 {plan.total_duration_minutes} 分钟 "
                f"超过用户上限 {max_allowed_minutes} 分钟"
            ),
        })

    if not plan.pois:
        return violations

    # 规则 2：距离约束（_filter_pois 已涵盖，但我们单独检查以获得详细原因）
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

    # 规则 3：营业时间（复用 activity_workflow._is_open_for_window）
    for poi in plan.pois:
        if not _is_open_for_window(poi, intent):
            violations.append({
                "rule": "business_hours",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} 营业时间 {poi.business_hours.open}–{poi.business_hours.close} "
                    f"不覆盖用户时间窗口 "
                    f"{intent.time_window.start}–{intent.time_window.end}"
                ),
            })

    # 规则 4：受众适配（复用 activity_workflow._matches_audience）
    for poi in plan.pois:
        if not _matches_audience(intent, poi):
            violations.append({
                "rule": "audience_fit",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} audience_fit 不满足 scenario={intent.scenario} 要求"
                ),
            })

    # 规则 5：评分门槛 — rating > 0 且 rating < 2.5 表示有实际评分数据但评分过低
    _RATING_THRESHOLD = 2.5
    for poi in plan.pois:
        if 0 < poi.rating < _RATING_THRESHOLD:
            violations.append({
                "rule": "low_rating",
                "poi_id": poi.id,
                "poi_name": poi.name,
                "detail": (
                    f"{poi.name} 评分 {poi.rating}/5 低于最低门槛 {_RATING_THRESHOLD}，"
                    "该地点口碑较差，已拒绝方案"
                ),
            })

    return violations
