"""
Agent 工作流共享状态类型定义。

设计原则：
- PlanningState 使用 dataclass（可变），方便 Orchestrator 协程直接 mutate
- 其余辅助类型使用 Pydantic，保持序列化/验证能力
- LangGraph 迁移路径：PlanningState 可直接映射为 LangGraph TypedDict State
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# 复用已有类型
from app.schemas.planning import ActionType, PlanSchema, POISchema, UserIntentSchema


# ---------------------------------------------------------------------------
# TraceEvent — 单条 Agent 执行记录，用于前端实时展示进度
# ---------------------------------------------------------------------------

TraceStatus = Literal["running", "done", "error"]


class TraceEvent(BaseModel):
    agent: str
    status: TraceStatus
    message: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )


# ---------------------------------------------------------------------------
# UserProfile — 用户画像（当前为轻量版本，后续可扩展）
# ---------------------------------------------------------------------------

class UserProfile(BaseModel):
    session_id: str
    preference_weights: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# RetrievalResult — Retrieval Node 的输出，聚合候选资源
# ---------------------------------------------------------------------------

class RetrievalResult(BaseModel):
    activities: list[POISchema] = Field(default_factory=list)
    restaurants: list[POISchema] = Field(default_factory=list)
    weather: str = ""
    route_info: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ExecutionResult — Execution Node 单个动作的执行结果
# ---------------------------------------------------------------------------

class ExecutionResult(BaseModel):
    action_type: ActionType
    success: bool
    detail: str


# ---------------------------------------------------------------------------
# PlanningState — 所有 Agent 节点共享的状态对象
#
# 使用 dataclass 而非 Pydantic，原因：
#   1. 节点运行时需要原地 mutate（而非创建新对象）
#   2. 避免重复 model_validate 带来的开销
#
# LangGraph 迁移说明：
#   将此 dataclass 替换为 TypedDict 或 langgraph.graph.MessageGraph State 即可，
#   字段名和含义保持不变。
# ---------------------------------------------------------------------------

@dataclass
class PlanningState:
    # 基础标识
    session_id: str
    raw_input: str

    # Intent 阶段：追问槽位，最多追问 2 次
    intent_clarification_count: int = 0
    intent: UserIntentSchema | None = None

    # Profile 阶段
    profile: UserProfile | None = None

    # Retrieval 阶段
    retrieval: RetrievalResult | None = None

    # Planning 阶段：候选方案列表
    candidate_plans: list[PlanSchema] = field(default_factory=list)

    # Verifier 阶段：回环计数，最多重生成 2 次
    plan_revision_count: int = 0

    # Verifier 阶段：记录拒绝原因，供 Planning Node 重试时参考
    # 每次 Verifier 拒绝后追加一批 dict，格式：{plan_id, plan_title, violations: [...]}
    verifier_rejection_reasons: list[dict[str, Any]] = field(default_factory=list)

    # 用户确认的方案
    confirmed_plan: PlanSchema | None = None

    # 用户偏好调整指令（如"换个户外的"）
    preference_adjustments: list[str] = field(default_factory=list)

    # Execution 阶段：各动作执行结果
    execution_results: list[ExecutionResult] = field(default_factory=list)

    # Trace：前端可订阅的 Agent 执行事件流
    trace: list[TraceEvent] = field(default_factory=list)

    @property
    def verifier_rejection_reason(self) -> str | None:
        """将最新一批拒绝原因格式化为字符串，供 PlanningNode 使用。

        PlanningNode 内部读取 state.verifier_rejection_reason（单数），
        而 VerifierNode 写入 state.verifier_rejection_reasons（复数，list）。
        此 property 桥接两者：取最后一批拒绝原因，汇总为可读字符串。

        Returns:
            格式化后的拒绝原因字符串；若无拒绝记录则返回 None。
        """
        if not self.verifier_rejection_reasons:
            return None

        # 取最后一批（最近一次 Verifier 运行的结果）
        last_batch = self.verifier_rejection_reasons[-1:]
        parts: list[str] = []
        for rejection in last_batch:
            plan_id = rejection.get("plan_id", "unknown")
            plan_title = rejection.get("plan_title", "")
            violations: list[dict[str, Any]] = rejection.get("violations", [])
            violation_details = "; ".join(
                v.get("detail", str(v)) for v in violations
            )
            parts.append(f"方案 {plan_id}（{plan_title}）：{violation_details}")

        return "\n".join(parts) if parts else None
