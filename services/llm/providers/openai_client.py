"""
OpenAI 兼容 HTTP 客户端

基于 stdlib urllib 实现，不引入任何外部 SDK。
兼容 OpenAI / DeepSeek / Ollama 等 OpenAI-compatible API。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from ..base import LLMError, LLMMessage, LLMResponse
from ..config import LLMConfig


class OpenAIClient:
    """
    OpenAI 兼容 HTTP 客户端。

    用法:
        config = LLMConfig(api_key="sk-...", model="gpt-4o-mini")
        client = OpenAIClient(config)
        response = client.chat([LLMMessage(role="user", content="你好")])
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self._base_url = config.base_url.rstrip("/")

    def chat(
        self,
        messages: List[LLMMessage],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        json_mode: bool = False,
    ) -> LLMResponse:
        payload = self._build_payload(messages, temperature, max_tokens, json_mode)
        url = f"{self._base_url}/chat/completions"

        last_error: Optional[Exception] = None
        for attempt in range(self.config.max_retries):
            try:
                raw_response = self._do_request(url, payload)
                return self._parse_response(raw_response)
            except LLMError as e:
                last_error = e
                if e.status_code is not None and 400 <= e.status_code < 500 and e.status_code != 429:
                    raise
                if attempt < self.config.max_retries - 1:
                    wait = min(2 ** attempt, 8)
                    time.sleep(wait)

        raise last_error  # type: ignore[misc]

    def _build_payload(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float],
        max_tokens: Optional[int],
        json_mode: bool,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature if temperature is not None else self.config.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.config.max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        return payload

    def _do_request(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            raise LLMError(
                f"API 请求失败: HTTP {e.code} — {error_body[:500]}",
                status_code=e.code,
                raw=error_body,
            ) from e
        except urllib.error.URLError as e:
            raise LLMError(f"网络错误: {e.reason}") from e
        except TimeoutError as e:
            raise LLMError(f"请求超时 ({self.config.timeout_seconds}s)") from e
        except OSError as e:
            raise LLMError(f"网络连接异常: {e}") from e

    def _parse_response(self, raw: Dict[str, Any]) -> LLMResponse:
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"API 响应格式异常: {e}", raw=raw) from e

        if not content:
            raise LLMError(f"API 返回空内容 (content={content!r})", raw=raw)

        usage_raw = raw.get("usage", {})
        return LLMResponse(
            content=content,
            usage={
                "prompt_tokens": usage_raw.get("prompt_tokens", 0),
                "completion_tokens": usage_raw.get("completion_tokens", 0),
                "total_tokens": usage_raw.get("total_tokens", 0),
            },
            model=raw.get("model", ""),
            raw=raw,
        )
