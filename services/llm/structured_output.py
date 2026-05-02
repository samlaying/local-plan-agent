"""
LLM 抽象层 — JSON 结构化输出解析

职责：
  - 在 prompt 末尾追加 JSON schema 指令
  - 解析 LLM 响应为 dict
  - 校验必要字段
  - 解析失败抛出 LLMParseError
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .base import LLMClient, LLMMessage, LLMResponse

try:
    from json_repair import repair_json
    _HAS_JSON_REPAIR = True
except ImportError:
    _HAS_JSON_REPAIR = False


# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------

class LLMParseError(Exception):
    """LLM 响应无法解析为预期的 JSON 结构。"""

    def __init__(self, message: str, raw_content: str = ""):
        super().__init__(message)
        self.raw_content = raw_content


# ---------------------------------------------------------------------------
# 结构化输出工具
# ---------------------------------------------------------------------------

def build_json_instruction(schema_description: str, required_fields: List[str]) -> str:
    """
    构建追加到 system prompt 的 JSON 格式指令。

    参数:
        schema_description: 对输出格式的自然语言描述
        required_fields: 必须包含的字段名列表

    返回:
        格式指令文本（追加到 system prompt 末尾）
    """
    fields_str = ", ".join(f'"{f}"' for f in required_fields)
    return (
        f"\n\n[输出格式要求]\n"
        f"你必须以 JSON 格式返回结果，不要包含其他内容。\n"
        f"格式说明：{schema_description}\n"
        f"必须包含以下字段：{fields_str}\n"
        f"不要使用 markdown 代码块包裹，直接返回纯 JSON。"
    )


def append_json_instruction(
    messages: List[LLMMessage],
    schema_description: str,
    required_fields: List[str],
) -> List[LLMMessage]:
    """
    在消息列表的 system 消息末尾追加 JSON 格式指令。
    如果没有 system 消息，则创建一个。
    返回新的消息列表（不修改原列表）。
    """
    instruction = build_json_instruction(schema_description, required_fields)
    new_messages = list(messages)

    # 查找 system 消息
    for i, msg in enumerate(new_messages):
        if msg.role == "system":
            new_messages[i] = LLMMessage(role="system", content=msg.content + instruction)
            return new_messages

    # 没有 system 消息，在开头插入一条
    new_messages.insert(0, LLMMessage(role="system", content=instruction.strip()))
    return new_messages


def parse_json_response(response: LLMResponse, required_fields: List[str]) -> Dict[str, Any]:
    """
    解析 LLM 响应为 dict，并校验必要字段。

    参数:
        response: LLM 响应对象
        required_fields: 必须包含的字段名列表

    返回:
        解析后的 dict

    异常:
        LLMParseError: 解析失败或缺少必要字段
    """
    content = response.content.strip()

    # 尝试直接解析
    data = _try_parse_json(content)

    if data is None:
        raise LLMParseError(
            f"无法将 LLM 响应解析为 JSON",
            raw_content=content,
        )

    # 校验必要字段
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise LLMParseError(
            f"JSON 响应缺少必要字段: {', '.join(missing)}",
            raw_content=content,
        )

    return data


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """
    尝试从文本中解析 JSON。
    支持直接 JSON 和 markdown 代码块包裹的 JSON。
    使用 json_repair 自动修复 LLM 常见的 JSON 格式问题。
    """
    # 1. 尝试用 json_repair 修复后解析
    if _HAS_JSON_REPAIR:
        try:
            repaired = repair_json(text)
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except Exception:
            pass  # 修复失败，回退到其他方法

    # 2. 先尝试提取 JSON 块，然后再用 json_repair 修复
    if _HAS_JSON_REPAIR:
        # 从 markdown 代码块中提取
        pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                repaired = repair_json(match.group(1).strip())
                result = json.loads(repaired)
                if isinstance(result, dict):
                    return result
            except Exception:
                pass

        # 找到 {} 括号配对提取
        stack = []
        json_start = None
        for i, char in enumerate(text):
            if char == '{':
                if not stack:
                    json_start = i
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack and json_start is not None:
                        try:
                            repaired = repair_json(text[json_start:i + 1])
                            result = json.loads(repaired)
                            if isinstance(result, dict):
                                return result
                        except Exception:
                            pass

    # 3. 回退到原来的直接解析（不修复）
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # 4. 从 markdown 代码块中提取（不修复）
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(1).strip())
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # 5. 找到 {} 括号配对提取（不修复）
    stack = []
    json_start = None
    for i, char in enumerate(text):
        if char == '{':
            if not stack:
                json_start = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and json_start is not None:
                    try:
                        result = json.loads(text[json_start:i + 1])
                        if isinstance(result, dict):
                            return result
                    except (json.JSONDecodeError, ValueError):
                        pass

    return None
