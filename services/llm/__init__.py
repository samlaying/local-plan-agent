"""
services.llm — LLM 抽象层

提供统一的 LLM 客户端接口，支持多 provider 切换。
当前支持：OpenAI 兼容接口（OpenAI / DeepSeek / Ollama）、Mock 测试客户端。
"""
from .base import LLMClient, LLMError, LLMMessage, LLMResponse
from .config import LLMConfig
from .structured_output import LLMParseError, parse_json_response

__all__ = [
    "LLMClient",
    "LLMConfig",
    "LLMError",
    "LLMMessage",
    "LLMParseError",
    "LLMResponse",
    "parse_json_response",
]
