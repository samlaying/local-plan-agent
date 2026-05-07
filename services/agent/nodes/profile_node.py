"""
ProfileNode — 读取用户历史偏好，在 Intent 解析后、Retrieval 前运行。

职责：
1. 根据 state.session_id 从 UserProfileRepository 查询历史偏好
2. 若存在历史记录：
   - 将 preference_weights 中权重 >= 0.5 的 tag 追加到 state.intent.soft_preferences（去重）
   - 将查到的 UserProfileSchema 转换为 UserProfile 存入 state.profile
3. 若无历史记录：跳过，不修改状态
4. 向 state.trace 追加 running / done / error TraceEvent

错误处理：数据库查询失败时记录 warning 日志 + error TraceEvent，不中断流程。
Profile 是增强项，不是必须的，节点失败不应阻塞后续节点。

注意：state.profile 类型为 UserProfile（state/types.py 的轻量版本），
而 UserProfileRepository.get() 返回 UserProfileSchema（schemas/planning.py 的完整版本）。
节点在写入 state.profile 时做类型转换，仅保留 session_id 和 preference_weights。
"""

from __future__ import annotations

import logging

from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, TraceEvent, UserProfile
from app.repositories.user_profile_repository import UserProfileRepository

logger = logging.getLogger(__name__)

# 偏好权重阈值：权重 >= WEIGHT_THRESHOLD 的 tag 才被采纳为 soft_preferences
WEIGHT_THRESHOLD: float = 0.5


class ProfileNode(BaseNode):
    """读取用户历史偏好，补充 state.intent.soft_preferences。

    依赖注入：
        repository — UserProfileRepository 实例（方便单元测试替换为 mock）
    """

    def __init__(self, repository: UserProfileRepository | None = None) -> None:
        self._repository = repository or UserProfileRepository()

    # ------------------------------------------------------------------
    # BaseNode.run
    # ------------------------------------------------------------------

    async def run(self, state: PlanningState) -> PlanningState:
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message=f"正在查询用户历史偏好（session_id={state.session_id}）...",
        ))

        try:
            profile_schema = await self._repository.get(state.session_id)
        except Exception as exc:
            logger.warning(
                "[%s] 查询用户偏好失败，跳过 Profile 增强：%s",
                self.name,
                exc,
                exc_info=True,
            )
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message=f"查询用户偏好失败（{type(exc).__name__}），已跳过 Profile 增强，流程继续",
            ))
            return state

        if profile_schema is None:
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message="未找到历史偏好记录，跳过 Profile 增强",
            ))
            logger.info("[%s] 无历史 Profile，session_id=%s", self.name, state.session_id)
            return state

        # 将 preference_weights >= WEIGHT_THRESHOLD 的 tag 补充到 soft_preferences（去重）
        high_weight_tags = [
            tag
            for tag, weight in profile_schema.preference_weights.items()
            if weight >= WEIGHT_THRESHOLD
        ]

        added_tags: list[str] = []
        if state.intent is not None and high_weight_tags:
            existing = set(state.intent.soft_preferences)
            for tag in high_weight_tags:
                if tag not in existing:
                    state.intent.soft_preferences.append(tag)
                    existing.add(tag)
                    added_tags.append(tag)

        # 将 UserProfileSchema 转换为 UserProfile 存入 state.profile
        state.profile = UserProfile(
            session_id=profile_schema.session_id,
            preference_weights=dict(profile_schema.preference_weights),
        )

        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=(
                f"历史偏好加载完成：{len(profile_schema.preference_weights)} 个权重记录，"
                f"新增 {len(added_tags)} 个 soft_preferences"
                + (f"（{', '.join(added_tags)}）" if added_tags else "")
            ),
        ))
        logger.info(
            "[%s] Profile 加载完成：session_id=%s，高权重 tag=%d，新增偏好=%d",
            self.name,
            state.session_id,
            len(high_weight_tags),
            len(added_tags),
        )
        return state
