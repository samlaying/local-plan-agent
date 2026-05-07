"""
BaseNode — 所有 Agent 节点必须实现的抽象接口。

设计原则：
- 节点是纯函数风格：接收完整 PlanningState，返回修改后的 PlanningState
- 节点不持有业务状态（self 上只允许挂载配置/依赖，不挂载运行时数据）
- 不直接访问数据库或 HTTP（除非该节点明确"拥有"该职责）

LangGraph 迁移路径：
  将 BaseNode.run 的签名改为 LangGraph node callable 即可：
    async def run(state: dict) -> dict   (partial state patch)
  当前返回完整 state 是为了在自定义状态机里保持简单；
  迁移时只需改为返回 dict patch 并注册到 StateGraph。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from agent.state.types import PlanningState


class BaseNode(ABC):
    """所有 Agent 节点的抽象基类。

    子类实现 `run` 方法：
    - 读取 state 中所需字段
    - 执行节点逻辑（可以是 LLM 调用、工具调用、规则计算等）
    - 将结果写入 state 对应字段
    - 向 state.trace 追加 TraceEvent
    - 返回修改后的 state

    注意：直接 mutate state 字段（dataclass 是可变的），
    而不是创建新的 PlanningState 对象，以避免不必要的开销。
    """

    @property
    def name(self) -> str:
        """节点名称，用于 TraceEvent.agent 字段。默认取类名。"""
        return self.__class__.__name__

    @abstractmethod
    async def run(self, state: PlanningState) -> PlanningState:
        """执行节点逻辑。

        Args:
            state: 当前规划状态（可直接 mutate）

        Returns:
            修改后的 state（即传入的同一对象）
        """
        ...
