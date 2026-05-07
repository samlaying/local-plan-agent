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
# 共享常量
# ---------------------------------------------------------------------------

# Intent 阶段最大追问次数（Orchestrator 和 IntentParserNode 共享此常量）
MAX_CLARIFICATION_COUNT = 2


# ---------------------------------------------------------------------------
# SearchStrategy — 单次并行检索的搜索策略配置
# ---------------------------------------------------------------------------

class SearchStrategy(BaseModel):
    """单个方案的搜索策略，描述用哪些关键词和 POI 类型搜索候选池。"""

    style: str
    """方案风格名，如"户外自然"，传给 RetrievalResult.style 和 LLM prompt。"""

    activity_keywords: str
    """高德 place/around 的 keywords 参数，如"公园|广场|亲子|自然"。"""

    activity_types: str
    """高德 POI 类型代码，如"110000|160000"。"""

    restaurant_keywords: str
    """餐厅搜索关键词，如"健康轻食|儿童友好"。"""

    restaurant_types: str = "050000"
    """固定餐饮服务类型代码（默认 050000），一般不需要改动。"""


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
    rejected_by_business_hours: list[dict[str, Any]] = Field(
        default_factory=list,
        description="因营业时间不覆盖用户时间窗口而被过滤的 POI 记录。"
        " 每条记录包含：poi_id、name、reason、business_hours、time_window。",
    )
    style: str = ""
    """来自 SearchStrategy.style，标识本结果集的风格，供 PlanningNode 参考。"""


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

    # 用户出发地（来自 WebSocket start 消息的 location 字段）
    origin_location: dict | None = None

    # Intent 阶段：追问槽位，最多追问 2 次
    intent_clarification_count: int = 0
    intent: UserIntentSchema | None = None

    # Intent 阶段：待发送给用户的追问文本（节点写入，Orchestrator 读后清空）
    pending_clarification: str | None = None

    # Profile 阶段
    profile: UserProfile | None = None

    # Retrieval 阶段
    retrieval: RetrievalResult | None = None

    # Retrieval 阶段：每个搜索策略独立的候选集（多策略并行搜索时填充）
    retrieval_strategies: list[RetrievalResult] = field(default_factory=list)

    # Planning 阶段：候选方案列表
    candidate_plans: list[PlanSchema] = field(default_factory=list)

    # Verifier 阶段：回环计数，最多重生成 2 次
    plan_revision_count: int = 0

    # Verifier 阶段：记录拒绝原因，供 Planning Node 重试时参考
    # 外层列表每个元素是一次 Verifier 运行的拒绝批次（list[dict]）
    # 格式：[[{plan_id, plan_title, violations: [...]}, ...], ...]
    verifier_rejection_reasons: list[list[dict[str, Any]]] = field(default_factory=list)

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
        last_batch = self.verifier_rejection_reasons[-1]
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
