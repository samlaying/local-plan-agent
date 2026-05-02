"""
SessionManager — 管理所有活跃 WebSocket 会话的内存存储。

设计说明：
- 使用 in-memory dict，key = session_id
- asyncio 是单线程协作式调度，dict 操作本身是原子的，
  不需要额外的 asyncio.Lock（仅在 create/get/remove 无 await 的前提下成立）
- 如果未来 create 需要做 async 初始化（如查 DB 加载历史状态），
  需要在方法内部加 Lock，此时可将 _lock = asyncio.Lock() 加回来

单例使用方式：
    from agent.session.manager import session_manager
    session = session_manager.create(session_id, ws, raw_input)
"""

from __future__ import annotations

from fastapi import WebSocket

from agent.session.session import Session
from agent.state.types import PlanningState  # used in create() to build initial state


class SessionManager:
    """管理活跃 Session 的单例容器。

    所有方法均为同步操作（无 await），asyncio 场景下不需要额外锁。
    若引入需要 await 的操作，请在方法中添加 asyncio.Lock。
    """

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, session_id: str, ws: WebSocket, raw_input: str = "") -> Session:
        """创建并注册新 Session。

        若 session_id 已存在，会覆盖旧 Session（旧连接已断开的情况）。

        Args:
            session_id: 唯一会话 ID，通常由 WebSocket 路由生成（uuid4）。
            ws: FastAPI WebSocket 连接对象。
            raw_input: 用户首条输入文本，用于初始化 PlanningState。

        Returns:
            新创建的 Session 实例。
        """
        state = PlanningState(session_id=session_id, raw_input=raw_input)
        session = Session(session_id=session_id, ws=ws, state=state)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        """根据 session_id 获取 Session。

        Returns:
            Session 实例，若不存在则返回 None。
        """
        return self._sessions.get(session_id)

    def remove(self, session_id: str) -> None:
        """移除并销毁 Session（WebSocket 断开时调用）。

        若 session_id 不存在，静默忽略。
        """
        self._sessions.pop(session_id, None)

    @property
    def active_count(self) -> int:
        """当前活跃 Session 数量，用于监控。"""
        return len(self._sessions)


# 模块级全局单例 — FastAPI 启动时自动初始化
session_manager = SessionManager()
