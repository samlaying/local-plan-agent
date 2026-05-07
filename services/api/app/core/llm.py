"""
LLM 客户端工厂（应用层）

从 app.core.config.settings 读取 LLM 配置，返回单例 LLMClient。
api_key 非空 → OpenAIClient；api_key 为空 → MockLLMClient（本地开发）。
"""
from __future__ import annotations

from llm.base import LLMClient
from llm.config import LLMConfig
from llm.factory import create_llm_client

from app.core.config import settings

_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """返回全局单例 LLM 客户端。首次调用时按 settings 初始化。"""
    global _client
    if _client is None:
        config = LLMConfig(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        _client = create_llm_client(config)
    return _client
