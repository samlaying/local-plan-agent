from __future__ import annotations

import asyncio
from collections import defaultdict

from app.schemas.planning import ActionSchema
from agent.state.types import PlanningState, TraceEvent, ExecutionResult

# Mock detail strings keyed by action type
_MOCK_DETAIL: dict[str, str] = {
    "navigation": "导航链接已生成（mock）",
    "reservation": "预约已提交（mock）",
    "ticket": "票务已预订（mock）",
    "queue": "已取号（mock）",
    "message": "行程摘要已生成（mock）",
}


def _mock_detail(action_type: str) -> str:
    return _MOCK_DETAIL.get(action_type, f"{action_type} 已执行（mock）")


async def _execute_group(actions: list[ActionSchema]) -> list[ExecutionResult]:
    """Execute a list of same-type actions sequentially and return their results."""
    results: list[ExecutionResult] = []
    for action in actions:
        # Each action within a group executes sequentially.
        # In a real implementation this would await an actual I/O call.
        result = ExecutionResult(
            action_type=action.type,
            success=True,
            detail=_mock_detail(action.type),
        )
        results.append(result)
    return results


class ExecutionNode:
    """Executes all actions in state.confirmed_plan.actions.

    Groups actions by type; within each group actions run sequentially.
    Different groups run concurrently via asyncio.gather (up to 4-way parallelism).
    Writes results to state.execution_results.
    """

    def __init__(self, use_mock: bool = True) -> None:
        self.use_mock = use_mock

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent="ExecutionNode",
            status="running",
            message="开始执行动作...",
        ))

        if state.confirmed_plan is None:
            state.trace.append(TraceEvent(
                agent="ExecutionNode",
                status="done",
                message="无 confirmed_plan，跳过执行",
            ))
            return state

        actions = state.confirmed_plan.actions

        # Group actions by type, preserving order within each group
        groups: dict[str, list[ActionSchema]] = defaultdict(list)
        for action in actions:
            groups[action.type].append(action)

        # Run all groups concurrently; within each group order is preserved
        group_results: list[list[ExecutionResult]] = await asyncio.gather(
            *(_execute_group(group_actions) for group_actions in groups.values())
        )

        # Flatten results preserving original action order
        all_results: list[ExecutionResult] = []
        for group in group_results:
            all_results.extend(group)

        state.execution_results = all_results

        state.trace.append(TraceEvent(
            agent="ExecutionNode",
            status="done",
            message=f"执行完成，共 {len(all_results)} 项动作",
        ))

        return state
