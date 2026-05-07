"""
LLM 抽象层 — 配置
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMConfig:
    """
    LLM 客户端配置。

    通过 provider 和 base_url 切换后端：
      - OpenAI:   provider="openai",   base_url="https://api.openai.com/v1"
      - DeepSeek: provider="deepseek", base_url="https://api.deepseek.com/v1"
      - Ollama:   provider="ollama",   base_url="http://localhost:11434/v1"
    """
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout_seconds: int = 30
    max_retries: int = 3
