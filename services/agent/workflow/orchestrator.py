"""
Orchestrator — 管理整个 Agent 工作流生命周期的异步协程。

Phase 2：接入真实 Agent 节点（IntentParserNode → RetrievalNode → PlanningNode → VerifierNode）。

消息类型（服务端发送）：
  session_ready / trace / ask / plans_ready /
  execution_preview / execution_result / done / error

消息类型（客户端发送）：
  start / user_reply / plan_confirmed / plan_rejected /
  execution_confirmed / cancel
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from agent.nodes.intent_parser import IntentParserNode
from agent.nodes.planning_node import PlanningNode
from agent.nodes.retrieval_node import RetrievalNode
from agent.nodes.verifier_node import VerifierNode
from agent.session.session import Session
from agent.state.types import PlanningState
from app.core.llm import get_llm_client

logger = logging.getLogger(__name__)

# Planning + Verifier 最大回环次数
MAX_PLAN_REVISION = 2

# Clarification 最大追问次数（与 IntentParserNode.MAX_CLARIFICATION_COUNT 保持一致）
MAX_CLARIFICATION_COUNT = 2


# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

async def _send(session: Session, msg: dict[str, Any]) -> None:
    """统一推送入口，附加服务端时间戳。"""
    msg.setdefault("ts", datetime.now(tz=timezone.utc).isoformat())
    await session.send_json(msg)


async def _wait_message(session: Session) -> dict[str, Any]:
    """阻塞等待队列中下一条用户消息，返回已解析的 dict。"""
    raw = await session.queue.get()
    return json.loads(raw)


async def _run_node_and_stream(session: Session, node: Any) -> None:
    """运行节点并将新增 trace 事件推送给前端。

    跳过 `[clarification]` 前缀的事件（这些由 Orchestrator 单独处理为 ask 消息）。

    Args:
        session: 当前会话（含 state 和 send_json）。
        node: 实现 BaseNode.run(state) -> state 的节点实例。
    """
    state = session.state
    trace_len_before = len(state.trace)

    await node.run(state)

    # 推送本次节点新增的 trace 事件（跳过 clarification 事件）
    new_events = state.trace[trace_len_before:]
    for event in new_events:
        if event.message.startswith("[clarification]"):
            continue
        await _send(session, {
            "type": "trace",
            "agent": event.agent,
            "status": event.status,
            "message": event.message,
        })


def _extract_clarification(state: PlanningState) -> str | None:
    """从 state.trace 中倒序扫描，找到最新的 [clarification] 事件并返回问题文本。

    Returns:
        去掉 `[clarification] ` 前缀后的问题文本；若未找到则返回 None。
    """
    for event in reversed(state.trace):
        if event.message.startswith("[clarification]"):
            return event.message[len("[clarification]"):].strip()
    return None


# ---------------------------------------------------------------------------
# 主协程
# ---------------------------------------------------------------------------

async def run_orchestrator(session: Session) -> None:
    """Orchestrator 主协程，由 WebSocket route handler 通过 asyncio.create_task 启动。

    完整生命周期：
      1. 等待 start 消息
      2. Intent 解析循环（最多 MAX_CLARIFICATION_COUNT 轮追问）
      3. Retrieval
      4. Planning + Verifier 回环（最多 MAX_PLAN_REVISION 次）
      5. 发送 plans_ready
      6. 等待 plan_confirmed / plan_rejected
      7. Execution 阶段（现有 mock 逻辑保持不变）
    """
    try:
        # 初始化节点（共享一个 LLM client）
        llm_client = get_llm_client()
        intent_node = IntentParserNode(llm_client=llm_client)
        retrieval_node = RetrievalNode()
        planning_node = PlanningNode(llm_client=llm_client)
        verifier_node = VerifierNode()

        await _phase_start(session)
        await _phase_intent(session, intent_node)
        await _phase_retrieval(session, retrieval_node)
        await _phase_planning_loop(session, planning_node, verifier_node)
        plans = await _phase_send_plans_ready(session)
        confirmed_plan = await _phase_plan_selection(session, plans)
        if confirmed_plan is None:
            await _send(session, {"type": "done", "reason": "plan_rejected"})
            return
        await _phase_execution(session, confirmed_plan)
    except asyncio.CancelledError:
        logger.info("Orchestrator cancelled for session %s", session.session_id)
        raise
    except Exception as exc:
        logger.exception("Orchestrator error for session %s: %s", session.session_id, exc)
        await _send(session, {"type": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# Phase 1: 等待 start 消息
# ---------------------------------------------------------------------------

async def _phase_start(session: Session) -> None:
    """等待客户端发来 start 消息；其他消息类型直接忽略。"""
    while True:
        msg = await _wait_message(session)
        if msg.get("type") == "start":
            payload = msg.get("payload", {})
            query = payload.get("query", "")
            location = payload.get("location", {})
            session.state.raw_input = query
            session.state.intent = None
            # 将 location 暂存在 session 上供 Retrieval 使用
            session._location_raw = location  # type: ignore[attr-defined]
            return
        logger.debug("Ignored message before start: %s", msg.get("type"))


# ---------------------------------------------------------------------------
# Phase 2: Intent 解析循环（最多 MAX_CLARIFICATION_COUNT 轮追问）
# ---------------------------------------------------------------------------

async def _phase_intent(session: Session, intent_node: IntentParserNode) -> None:
    """运行 IntentParserNode，有追问时向前端发 ask 消息并等待 user_reply。"""
    clarification_round = 0

    while True:
        await _run_node_and_stream(session, intent_node)

        if session.state.intent is not None:
            # 意图解析成功，退出循环
            return

        # intent 为 None 表示需要追问
        clarification_round += 1
        if clarification_round > MAX_CLARIFICATION_COUNT:
            # 超过追问上限，强制退出（IntentParserNode 内部会用默认值填充）
            logger.warning(
                "Session %s: clarification rounds exhausted, proceeding with defaults",
                session.session_id,
            )
            return

        question = _extract_clarification(session.state)
        if question is None:
            logger.warning(
                "Session %s: intent is None but no clarification found in trace, "
                "proceeding without further clarification",
                session.session_id,
            )
            return

        # 发送追问给前端
        await _send(session, {
            "type": "ask",
            "question": question,
            "round": clarification_round,
        })

        # 等待用户回复
        while True:
            msg = await _wait_message(session)
            if msg.get("type") == "user_reply":
                user_reply = msg.get("text", "")
                # 将回复拼接到原始输入，供节点下一轮解析
                session.state.raw_input = session.state.raw_input + " " + user_reply
                break
            if msg.get("type") == "cancel":
                raise asyncio.CancelledError
            logger.debug("Ignored message while waiting for user_reply: %s", msg.get("type"))


# ---------------------------------------------------------------------------
# Phase 3: Retrieval
# ---------------------------------------------------------------------------

async def _phase_retrieval(session: Session, retrieval_node: RetrievalNode) -> None:
    """运行 RetrievalNode，推送 trace 事件。"""
    await _run_node_and_stream(session, retrieval_node)


# ---------------------------------------------------------------------------
# Phase 4: Planning + Verifier 回环（最多 MAX_PLAN_REVISION 次）
# ---------------------------------------------------------------------------

async def _phase_planning_loop(
    session: Session,
    planning_node: PlanningNode,
    verifier_node: VerifierNode,
) -> None:
    """运行 Planning → Verifier 回环，有拒绝时最多重生成 MAX_PLAN_REVISION 次。"""
    for iteration in range(MAX_PLAN_REVISION + 1):
        revision_before = session.state.plan_revision_count

        await _run_node_and_stream(session, planning_node)
        await _run_node_and_stream(session, verifier_node)

        revision_after = session.state.plan_revision_count

        # plan_revision_count 没有增加，说明 Verifier 通过了
        if revision_after == revision_before:
            break

        if iteration < MAX_PLAN_REVISION:
            logger.info(
                "Session %s: verifier rejected plans (revision %d/%d), retrying planning",
                session.session_id,
                revision_after,
                MAX_PLAN_REVISION,
            )
        else:
            logger.warning(
                "Session %s: max plan revisions reached (%d), using current plans",
                session.session_id,
                MAX_PLAN_REVISION,
            )


# ---------------------------------------------------------------------------
# Phase 5: 发送 plans_ready
# ---------------------------------------------------------------------------

async def _phase_send_plans_ready(session: Session) -> list[dict[str, Any]]:
    """将 state.candidate_plans 序列化并发送 plans_ready 消息。

    Returns:
        序列化后的 plans_data 列表（供后续 plan_confirmed 查找用）。
    """
    plans_data = [plan.model_dump(mode="json") for plan in session.state.candidate_plans]

    intent_data = (
        session.state.intent.model_dump(mode="json")
        if session.state.intent is not None
        else {}
    )

    await _send(session, {
        "type": "plans_ready",
        "plans": plans_data,
        "intent": intent_data,
    })

    return plans_data


# ---------------------------------------------------------------------------
# Phase 6: 等待用户选择方案
# ---------------------------------------------------------------------------

async def _phase_plan_selection(
    session: Session,
    plans: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """等待 plan_confirmed 或 plan_rejected 消息。

    Returns:
        已确认的 plan dict，或 None（用户拒绝）。
    """
    while True:
        msg = await _wait_message(session)
        msg_type = msg.get("type")

        if msg_type == "plan_confirmed":
            plan_id = msg.get("plan_id")
            confirmed = next(
                (p for p in plans if p.get("id") == plan_id),
                plans[0] if plans else None,
            )
            return confirmed

        if msg_type == "plan_rejected":
            return None

        if msg_type == "cancel":
            return None

        logger.debug("Ignored message in plan_selection phase: %s", msg_type)


# ---------------------------------------------------------------------------
# Phase 7: 执行预览 + 确认（保持现有 mock 逻辑不变）
# ---------------------------------------------------------------------------

async def _phase_execution(
    session: Session,
    confirmed_plan: dict[str, Any],
) -> None:
    """发送 execution_preview，等待 execution_confirmed，再发 execution_result + done。"""
    actions = confirmed_plan.get("actions", [])
    await _send(session, {
        "type": "execution_preview",
        "plan_id": confirmed_plan.get("id"),
        "plan_title": confirmed_plan.get("title"),
        "actions": actions,
        "summary": f"即将执行 {len(actions)} 项操作，请确认",
    })

    while True:
        msg = await _wait_message(session)
        msg_type = msg.get("type")

        if msg_type == "execution_confirmed":
            break
        if msg_type == "cancel":
            await _send(session, {"type": "done", "reason": "execution_cancelled"})
            return

        logger.debug("Ignored message in execution phase: %s", msg_type)

    execution_results = _build_mock_execution_results(actions)

    await _send(session, {
        "type": "execution_result",
        "plan_id": confirmed_plan.get("id"),
        "results": execution_results,
        "success_count": sum(1 for r in execution_results if r["success"]),
        "total_count": len(execution_results),
    })

    await _send(session, {
        "type": "done",
        "reason": "execution_complete",
        "plan_id": confirmed_plan.get("id"),
    })


def _build_mock_execution_results(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """根据 actions 列表构建 mock 执行结果。"""
    results: list[dict[str, Any]] = []
    for action in actions:
        action_type = action.get("type", "unknown")
        if action_type == "navigation":
            detail = "导航链接已生成（mock）"
            success = True
        elif action_type == "reservation":
            detail = "预约已提交，等待商家确认（mock）"
            success = True
        elif action_type == "ticket":
            detail = "票务已预订（mock）"
            success = True
        elif action_type == "queue":
            detail = "已取号，预计等待时间见原行程（mock）"
            success = True
        elif action_type == "message":
            detail = "行程摘要已生成，可手动分享"
            success = True
        else:
            detail = f"{action_type} 动作已 mock 执行"
            success = True

        results.append({
            "action_id": action.get("id"),
            "action_type": action_type,
            "title": action.get("title"),
            "success": success,
            "detail": detail,
        })
    return results
