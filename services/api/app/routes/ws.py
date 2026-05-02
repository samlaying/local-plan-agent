"""
WebSocket 路由 — /ws/planning

连接生命周期：
  1. 握手成功 → 创建 Session → 发送 session_ready
  2. 启动 orchestrator 协程（asyncio.create_task）
  3. 持续接收客户端消息 → 解析 JSON → 根据 type 路由
     - start: 将 query/location 写入 session.state，放入 session.queue
     - 其他（user_reply / plan_confirmed / plan_rejected /
              execution_confirmed / cancel）：直接放入 session.queue
  4. 连接断开 → 取消 orchestrator task → 清理 Session
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agent.session.manager import session_manager
from agent.workflow.orchestrator import run_orchestrator

router = APIRouter()
logger = logging.getLogger(__name__)

# 允许客户端直接放入队列的消息类型（orchestrator 自行处理语义）
_QUEUE_PASSTHROUGH_TYPES = frozenset({
    "start",
    "user_reply",
    "plan_confirmed",
    "plan_rejected",
    "execution_confirmed",
    "cancel",
})


@router.websocket("/ws/planning")
async def ws_planning(websocket: WebSocket) -> None:
    """WebSocket 规划端点。

    每次连接对应一个完整的规划会话。
    """
    await websocket.accept()

    session_id = uuid4().hex
    session = session_manager.create(session_id=session_id, ws=websocket)

    # 发送 session_ready，告知前端会话已就绪
    await websocket.send_json({
        "type": "session_ready",
        "session_id": session_id,
        "ts": datetime.now(tz=timezone.utc).isoformat(),
    })

    # 启动 orchestrator 协程
    orchestrator_task = asyncio.create_task(
        run_orchestrator(session),
        name=f"orchestrator-{session_id}",
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Session %s: received non-JSON message, ignored", session_id)
                continue

            msg_type = msg.get("type")

            if msg_type in _QUEUE_PASSTHROUGH_TYPES:
                # 所有业务消息直接放入队列，由 orchestrator 消费
                await session.queue.put(raw)
            else:
                logger.warning(
                    "Session %s: unknown message type '%s', ignored",
                    session_id,
                    msg_type,
                )

    except WebSocketDisconnect:
        logger.info("Session %s disconnected", session_id)
    except Exception as exc:
        logger.exception("Session %s unexpected error: %s", session_id, exc)
    finally:
        # 取消 orchestrator 协程
        if not orchestrator_task.done():
            orchestrator_task.cancel()
            try:
                await orchestrator_task
            except asyncio.CancelledError:
                pass

        session_manager.remove(session_id)
        logger.info("Session %s cleaned up", session_id)
