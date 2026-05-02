"""
LLM 抽象层 — 核心类型与协议
提供统一的 LLM 客户端接口，供叙事引擎、NPC 对话、世界响应等子系统使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# 数据类型
# ---------------------------------------------------------------------------

@dataclass
class LLMMessage:
    """单条对话消息。"""
    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """LLM 返回的标准响应。"""
    content: str
    usage: Dict[str, int] = field(default_factory=dict)   # prompt_tokens, completion_tokens, total_tokens
    model: str = ""
    raw: Optional[Any] = None   # 原始 API 响应，供调试用


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class LLMError(Exception):
    """LLM 调用失败（网络错误、API 错误、超时等）。"""

    def __init__(self, message: str, status_code: Optional[int] = None, raw: Optional[Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw = raw


# ---------------------------------------------------------------------------
# 客户端协议
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMClient(Protocol):
    """
    LLM 客户端协议。
    所有 provider 实现此接口即可被子系统使用。
    """

    def chat(
        self,
        messages: List[LLMMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        """
        发送对话请求并返回响应。

        参数:
            messages: 对话消息列表
            temperature: 采样温度（覆盖配置默认值）
            max_tokens: 最大生成 token 数（覆盖配置默认值）
            json_mode: 是否要求 JSON 格式输出
        """
        ...
