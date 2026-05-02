"""
测试用 Mock LLM 客户端

可配置固定响应，记录调用历史，供所有 LLM 子系统测试使用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import LLMMessage, LLMResponse


@dataclass
class CallRecord:
    """一次 chat 调用的记录。"""
    messages: List[LLMMessage]
    temperature: Optional[float]
    max_tokens: Optional[int]
    json_mode: bool


class MockLLMClient:
    """
    Mock LLM 客户端。

    用法:
        client = MockLLMClient(default_response="你好世界")
        resp = client.chat([LLMMessage(role="user", content="你好")])

        # 多次调用返回不同响应（按顺序消费）
        client = MockLLMClient(responses=["第一次", "第二次"])
    """

    def __init__(
        self,
        default_response: str = "",
        responses: Optional[List[str]] = None,
        model: str = "mock-model",
    ):
        self._default_response = default_response
        self._responses: List[str] = list(responses) if responses else []
        self._response_index = 0
        self._model = model
        self.call_history: List[CallRecord] = []

    def chat(
        self,
        messages: List[LLMMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.call_history.append(CallRecord(
            messages=list(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
        ))

        if self._responses:
            content = self._responses[min(self._response_index, len(self._responses) - 1)]
            self._response_index += 1
        else:
            content = self._default_response

        return LLMResponse(
            content=content,
            usage={
                "prompt_tokens": sum(len(m.content) for m in messages),
                "completion_tokens": len(content),
                "total_tokens": sum(len(m.content) for m in messages) + len(content),
            },
            model=self._model,
            raw=None,
        )
