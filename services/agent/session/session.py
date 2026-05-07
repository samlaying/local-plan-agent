"""
Session — 单个 WebSocket 连接的生命周期对象。

每个 WebSocket 连接对应一个 Session 实例：
- 持有连接对象（用于向前端推送消息）
- 持有一个 asyncio.Queue（Orchestrator 协程从中读取用户消息）
- 持有 PlanningState（当前规划进度）

注意：Session 本身不启动 Orchestrator 协程，
由 WebSocket route handler 在握手成功后负责启动。
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket

from agent.state.types import PlanningState


class Session:
    """单个 WebSocket 连接的生命周期容器。

    Attributes:
        session_id: 唯一会话标识，与 PlanningState.session_id 保持一致。
        ws: FastAPI WebSocket 连接对象。
        queue: Orchestrator 协程从此队列 await 用户消息（字符串 JSON）。
        state: 当前会话的规划状态。
    """

    def __init__(
        self,
        session_id: str,
        ws: WebSocket,
        state: PlanningState,
    ) -> None:
        self.session_id: str = session_id
        self.ws: WebSocket = ws
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.state: PlanningState = state

    async def send_json(self, data: dict[str, Any]) -> None:
        """向前端推送 JSON 消息。

        封装 WebSocket.send_json，统一入口便于后续添加错误处理或序列化逻辑。

        Args:
            data: 要发送的数据，必须是可 JSON 序列化的 dict。
        """
        await self.ws.send_json(data)
