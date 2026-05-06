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
import os
from datetime import datetime, timezone
from typing import Any

from agent.nodes.execution_node import ExecutionNode
from agent.nodes.feedback_node import FeedbackNode
from agent.nodes.intent_parser import IntentParserNode
from agent.nodes.planning_node import PlanningNode
from agent.nodes.profile_node import ProfileNode
from agent.nodes.retrieval_node import RetrievalNode
from agent.nodes.verifier_node import VerifierNode
from agent.session.session import Session
from agent.state.types import PlanningState
from app.core.llm import get_llm_client
from app.repositories.mock_poi_repository import MockPOIRepository
from app.repositories.user_profile_repository import UserProfileRepository
from tools.poi.amap_searcher import AmapSearcher
from tools.poi.mock_searcher import MockPOISearcher

logger = logging.getLogger(__name__)

# Planning + Verifier 最大回环次数
MAX_PLAN_REVISION = 2

# Clarification 最大追问次数（与 IntentParserNode.MAX_CLARIFICATION_COUNT 保持一致）
MAX_CLARIFICATION_COUNT = 2

# 用户拒绝方案后最大重检索规划次数
MAX_PREFERENCE_REVISION = 3


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

    Args:
        session: 当前会话（含 state 和 send_json）。
        node: 实现 BaseNode.run(state) -> state 的节点实例。
    """
    state = session.state
    trace_len_before = len(state.trace)

    await node.run(state)

    # 推送本次节点新增的 trace 事件
    new_events = state.trace[trace_len_before:]
    for event in new_events:
        await _send(session, {
            "type": "trace",
            "data": {
                "agent": event.agent,
                "status": event.status,
                "message": event.message,
            },
        })


# ---------------------------------------------------------------------------
# 主协程
# ---------------------------------------------------------------------------

async def run_orchestrator(session: Session) -> None:
    """Orchestrator 主协程，由 WebSocket route handler 通过 asyncio.create_task 启动。

    完整生命周期：
      1. 等待 start 消息
      2. Intent 解析循环（最多 MAX_CLARIFICATION_COUNT 轮追问）
      3. Retrieval → Planning + Verifier 回环 → plans_ready → 等待用户选择
         如果用户拒绝，读取 feedback 并追加到 preference_adjustments，重新从
         Retrieval 开始，最多重试 MAX_PREFERENCE_REVISION 次
      4. Execution 阶段（现有 mock 逻辑保持不变）
    """
    try:
        # 初始化节点（共享一个 LLM client）
        llm_client = get_llm_client()
        intent_node = IntentParserNode(llm_client=llm_client)
        profile_repo = UserProfileRepository()
        profile_node = ProfileNode(repository=profile_repo)
        use_mock_poi = os.getenv("USE_MOCK_POI", "true").lower() in ("true", "1", "yes")
        if use_mock_poi:
            poi_searcher = MockPOISearcher(repository=MockPOIRepository())
        else:
            poi_searcher = AmapSearcher()
        retrieval_node = RetrievalNode(searcher=poi_searcher)
        planning_node = PlanningNode(llm_client=llm_client)
        verifier_node = VerifierNode()

        await _phase_start(session)
        await _phase_intent(session, intent_node)
        await _run_node_and_stream(session, profile_node)

        confirmed_plan = await _phase_retrieval_planning_loop(
            session, retrieval_node, planning_node, verifier_node
        )

        if confirmed_plan is None:
            await _send(session, {"type": "done", "reason": "plan_rejected"})
            return

        await _phase_execution(session, confirmed_plan)
    except asyncio.CancelledError:
        logger.info("Orchestrator cancelled for session %s", session.session_id)
        raise
    except Exception as exc:
        logger.exception("Orchestrator error for session %s: %s", session.session_id, exc)
        await _send(session, {
            "type": "error",
            "data": {"message": str(exc), "recoverable": False},
        })


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
            # location 流入 PlanningState，由类型系统保证可见性
            session.state.origin_location = location if location else None
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

        question = session.state.pending_clarification
        # 读完后清空，避免下一轮误读
        session.state.pending_clarification = None
        if question is None:
            logger.warning(
                "Session %s: intent is None but pending_clarification is not set, "
                "proceeding without further clarification",
                session.session_id,
            )
            return

        # 发送追问给前端
        await _send(session, {
            "type": "ask",
            "data": {"question": question, "round": clarification_round},
        })

        # 等待用户回复
        while True:
            msg = await _wait_message(session)
            if msg.get("type") == "user_reply":
                user_reply = msg.get("payload", {}).get("text", "")
                # 将回复拼接到原始输入，供节点下一轮解析
                session.state.raw_input = session.state.raw_input + " " + user_reply
                break
            if msg.get("type") == "cancel":
                raise asyncio.CancelledError
            logger.debug("Ignored message while waiting for user_reply: %s", msg.get("type"))


# ---------------------------------------------------------------------------
# Phase 3+5+6: Retrieval → Planning+Verifier → plans_ready → 用户选择
#              用户拒绝时最多重试 MAX_PREFERENCE_REVISION 次
# ---------------------------------------------------------------------------

async def _phase_retrieval_planning_loop(
    session: Session,
    retrieval_node: RetrievalNode,
    planning_node: PlanningNode,
    verifier_node: VerifierNode,
) -> dict[str, Any] | None:
    """外层循环：用户拒绝方案后根据 feedback 重新检索规划。

    最多执行 MAX_PREFERENCE_REVISION 次完整的 Retrieval → Planning → plans_ready 流程。
    超过次数后直接发送 done 并返回 None。

    Returns:
        用户确认的 plan dict，或 None（用户拒绝且达到最大重试次数 / cancel）。
    """
    for revision in range(MAX_PREFERENCE_REVISION):
        # Phase 3: Retrieval
        await _phase_retrieval(session, retrieval_node)

        # Phase 4: Planning + Verifier 回环
        await _phase_planning_loop(session, planning_node, verifier_node)

        # Phase 5: 发送 plans_ready
        plans = await _phase_send_plans_ready(session)

        # Phase 6: 等待用户选择
        msg = await _phase_plan_selection_raw(session, plans)

        if msg is None:
            # cancel
            return None

        if msg["confirmed"]:
            return msg["plan"]

        # 用户拒绝 — 读取 feedback，追加到 preference_adjustments
        feedback: str = msg.get("feedback", "") or ""
        if feedback:
            session.state.preference_adjustments.append(feedback)

        remaining = MAX_PREFERENCE_REVISION - revision - 1
        if remaining == 0:
            logger.info(
                "Session %s: max preference revisions reached (%d), ending session",
                session.session_id,
                MAX_PREFERENCE_REVISION,
            )
            await _send(session, {"type": "done", "reason": "max_revisions_reached"})
            return None

        # 发送 trace 事件，告知用户正在重新规划
        await _send(session, {
            "type": "trace",
            "data": {
                "agent": "orchestrator",
                "status": "running",
                "message": "正在根据您的反馈重新规划...",
            },
        })

        logger.info(
            "Session %s: plan rejected (revision %d/%d), re-running retrieval+planning",
            session.session_id,
            revision + 1,
            MAX_PREFERENCE_REVISION,
        )

    # 不应到达此处，但作为安全兜底
    return None


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
        "data": {"plans": plans_data, "intent": intent_data},
    })

    return plans_data


# ---------------------------------------------------------------------------
# Phase 6: 等待用户选择方案（内部版，返回结构化结果）
# ---------------------------------------------------------------------------

async def _phase_plan_selection_raw(
    session: Session,
    plans: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """等待 plan_confirmed 或 plan_rejected 消息。

    Returns:
        dict with:
          {"confirmed": True, "plan": <plan dict>}  — 用户确认
          {"confirmed": False, "feedback": <str>}    — 用户拒绝（含可选 feedback）
        或 None（cancel）。
    """
    while True:
        msg = await _wait_message(session)
        msg_type = msg.get("type")

        if msg_type == "plan_confirmed":
            plan_id = msg.get("payload", {}).get("plan_id")
            confirmed = next(
                (p for p in plans if p.get("id") == plan_id),
                plans[0] if plans else None,
            )
            return {"confirmed": True, "plan": confirmed}

        if msg_type == "plan_rejected":
            feedback = msg.get("payload", {}).get("feedback", "") or msg.get("feedback", "") or ""
            return {"confirmed": False, "feedback": feedback}

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
        "data": {
            "plan_id": confirmed_plan.get("id"),
            "plan_title": confirmed_plan.get("title"),
            "actions": actions,
            "summary": f"即将执行 {len(actions)} 项操作，请确认",
        },
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

    # 用 ExecutionNode 执行动作（替代 mock 逻辑）
    execution_node = ExecutionNode()
    await _run_node_and_stream(session, execution_node)

    execution_results = [
        {
            "action_type": r.action_type,
            "success": r.success,
            "detail": r.detail,
        }
        for r in session.state.execution_results
    ]

    await _send(session, {
        "type": "execution_result",
        "data": {
            "results": execution_results,
            "all_success": all(r["success"] for r in execution_results),
        },
    })

    # FeedbackNode：fire-and-forget，在发 done 之前触发
    feedback_repo = UserProfileRepository()
    feedback_node = FeedbackNode(repository=feedback_repo)
    asyncio.create_task(feedback_node.run(session.state))

    await _send(session, {
        "type": "done",
        "reason": "execution_complete",
        "plan_id": confirmed_plan.get("id"),
    })
