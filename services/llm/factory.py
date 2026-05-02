"""
LLM 客户端工厂

根据配置返回合适的 LLM 客户端实例。
api_key 为空时自动返回 MockLLMClient（方便本地开发）。
"""
from __future__ import annotations

from .base import LLMClient
from .config import LLMConfig
from .providers.mock_client import MockLLMClient
from .providers.openai_client import OpenAIClient


def create_llm_client(config: LLMConfig) -> LLMClient:
    """
    工厂函数：根据配置返回 LLM 客户端。

    - api_key 非空 → OpenAIClient（真实调用）
    - api_key 为空 → MockLLMClient（本地开发/测试）
    """
    if config.api_key:
        return OpenAIClient(config)
    return MockLLMClient(
        default_response='{"error": "MockLLMClient: 请配置 LLM_API_KEY 以使用真实 LLM"}',
    )
