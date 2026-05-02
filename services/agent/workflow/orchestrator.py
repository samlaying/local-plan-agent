"""
Orchestrator — 管理整个 Agent 工作流生命周期的异步协程。

Phase 1 骨架版本：
- 不接入真实 Agent 节点
- 发送 mock trace 事件模拟各节点执行
- 复用已有 MockPOIRepository + activity_workflow 函数生成真实 mock plans
- 通过 session.queue 接收用户消息，通过 session.send_json 推送进度

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

from app.repositories.mock_poi_repository import MockPOIRepository
from app.services.activity_workflow import (
    UserLocationSchema,
    run_activity_workflow,
)
from agent.session.session import Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 内部辅助
# ---------------------------------------------------------------------------

_TRACE_NODES: list[tuple[str, str]] = [
    ("intent_node", "解析用户意图和场景..."),
    ("profile_node", "加载用户偏好画像..."),
    ("retrieval_node", "检索周边 POI 和餐厅候选..."),
    ("planning_node", "生成行程方案..."),
    ("verifier_node", "校验方案可行性..."),
]

# 每个节点 mock 运行时间（秒）—— 仅用于骨架演示
_NODE_DELAY_SECONDS: float = 0.6


async def _send(session: Session, msg: dict[str, Any]) -> None:
    """统一推送入口，附加服务端时间戳。"""
    msg.setdefault("ts", datetime.now(tz=timezone.utc).isoformat())
    await session.send_json(msg)


async def _wait_message(session: Session) -> dict[str, Any]:
    """阻塞等待队列中下一条用户消息，返回已解析的 dict。"""
    raw = await session.queue.get()
    return json.loads(raw)


# ---------------------------------------------------------------------------
# 主协程
# ---------------------------------------------------------------------------

async def run_orchestrator(session: Session) -> None:
    """Orchestrator 主协程，由 WebSocket route handler 通过 asyncio.create_task 启动。

    完整生命周期：
      1. 等待 start 消息
      2. 依次发送各节点的 running/done trace 事件
      3. 调用 activity_workflow 生成 plans，发送 plans_ready
      4. 等待 plan_confirmed / plan_rejected
      5. 收到 plan_confirmed → 发送 execution_preview，等待 execution_confirmed
      6. 收到 execution_confirmed → 发送 execution_result + done

    所有异常均捕获并发送 error 消息给前端，之后退出协程。
    """
    try:
        await _phase_start(session)
        await _phase_trace(session)
        plans = await _phase_generate_plans(session)
        confirmed_plan = await _phase_plan_selection(session, plans)
        if confirmed_plan is None:
            # 用户拒绝了所有方案，流程结束
            await _send(session, {"type": "done", "reason": "plan_rejected"})
            return
        await _phase_execution(session, confirmed_plan)
    except asyncio.CancelledError:
        # WebSocket 断开触发 task cancel，正常退出
        logger.info("Orchestrator cancelled for session %s", session.session_id)
        raise
    except Exception as exc:
        logger.exception("Orchestrator error for session %s: %s", session.session_id, exc)
        await _send(session, {"type": "error", "message": str(exc), "recoverable": False})


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
            # 将 query 和 location 写入 state 供后续节点使用
            session.state.raw_input = query
            session.state.intent = None  # 重置，等 intent_node 填入
            # 把 location 信息存在 state 的 profile 上（Phase 1 骨架：暂存为 dict）
            # TODO: 将 location 规范化为 UserLocationSchema 存入 state.retrieval
            session._location_raw = location  # type: ignore[attr-defined]
            return
        # 非 start 消息在流程未开始时忽略
        logger.debug("Ignored message before start: %s", msg.get("type"))


# ---------------------------------------------------------------------------
# Phase 2: 模拟各节点 trace 事件
# ---------------------------------------------------------------------------

async def _phase_trace(session: Session) -> None:
    """按顺序发送各节点的 running → done trace 事件。"""
    for agent_name, running_msg in _TRACE_NODES:
        # running
        await _send(session, {
            "type": "trace",
            "agent": agent_name,
            "status": "running",
            "message": running_msg,
        })
        await asyncio.sleep(_NODE_DELAY_SECONDS)
        # done
        await _send(session, {
            "type": "trace",
            "agent": agent_name,
            "status": "done",
            "message": f"{agent_name} 完成",
        })


# ---------------------------------------------------------------------------
# Phase 3: 生成 plans 并推送 plans_ready
# ---------------------------------------------------------------------------

async def _phase_generate_plans(session: Session) -> list[dict[str, Any]]:
    """复用 activity_workflow 生成 plans，发送 plans_ready 消息。"""
    raw_input = session.state.raw_input or "今天下午带孩子出去玩"
    location_raw: dict[str, Any] = getattr(session, "_location_raw", {})
    location = UserLocationSchema(
        city=location_raw.get("city", "Shanghai"),
        address=location_raw.get("address", "Home"),
        lat=location_raw.get("lat"),
        lng=location_raw.get("lng"),
    )

    # run_activity_workflow 是同步的，在线程池中执行避免阻塞事件循环
    loop = asyncio.get_running_loop()
    repo = MockPOIRepository()
    result = await loop.run_in_executor(
        None,
        lambda: run_activity_workflow(raw_input, location, repo),
    )

    # 将 PlanSchema 列表序列化为 JSON-safe dict
    plans_data = [plan.model_dump(mode="json") for plan in result.plans]

    await _send(session, {
        "type": "plans_ready",
        "plans": plans_data,
        "intent": result.intent.model_dump(mode="json"),
        "rejected_candidates": result.rejected_candidates,
    })

    return plans_data


# ---------------------------------------------------------------------------
# Phase 4: 等待用户选择方案
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
            payload = msg.get("payload", {})
            plan_id = payload.get("plan_id")
            # 从生成的 plans 中找到对应方案
            confirmed = next(
                (p for p in plans if p.get("id") == plan_id),
                plans[0] if plans else None,  # 兜底取第一个
            )
            session.state.confirmed_plan = None  # Phase 1 骨架：不写入 Pydantic 对象
            return confirmed

        if msg_type == "plan_rejected":
            # 用户明确拒绝，流程终止
            return None

        if msg_type == "cancel":
            return None

        # user_reply / 其他消息：暂时忽略（Phase 1 不支持追问）
        logger.debug("Ignored message in plan_selection phase: %s", msg_type)


# ---------------------------------------------------------------------------
# Phase 5: 执行预览 + 确认
# ---------------------------------------------------------------------------

async def _phase_execution(
    session: Session,
    confirmed_plan: dict[str, Any],
) -> None:
    """发送 execution_preview，等待 execution_confirmed，再发 execution_result + done。"""
    # 从已确认 plan 的 actions 构建 execution_preview
    actions = confirmed_plan.get("actions", [])
    await _send(session, {
        "type": "execution_preview",
        "plan_id": confirmed_plan.get("id"),
        "plan_title": confirmed_plan.get("title"),
        "actions": actions,
        "summary": f"即将执行 {len(actions)} 项操作，请确认",
    })

    # 等待用户确认执行
    while True:
        msg = await _wait_message(session)
        msg_type = msg.get("type")

        if msg_type == "execution_confirmed":
            break
        if msg_type == "cancel":
            await _send(session, {"type": "done", "reason": "execution_cancelled"})
            return

        logger.debug("Ignored message in execution phase: %s", msg_type)

    # Mock 执行结果
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
