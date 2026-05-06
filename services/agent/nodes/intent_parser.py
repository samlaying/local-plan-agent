"""
IntentParserNode — Agent 工作流第一个节点。

职责：
  - 调用 LLM 从用户自然语言输入提取结构化意图
  - 检测必填槽位是否完整（出发地、时间窗口、人群组成）
  - 槽位缺失时生成追问，最多追问 2 次（MAX_CLARIFICATION_COUNT）
  - 超过追问上限后用合理默认值填充缺失槽位继续流程
  - 提取完成后判断 scenario 并写入 UserIntentSchema

LangGraph 迁移路径：
  将 run 方法签名改为 async def run(state: dict) -> dict（partial patch）即可。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from app.schemas.planning import (
    ParticipantSchema,
    TimeWindowSchema,
    TravelMode,
    UserIntentSchema,
)
from agent.nodes.base import BaseNode
from agent.state.types import PlanningState, TraceEvent
from llm.base import LLMClient, LLMError, LLMMessage
from llm.structured_output import LLMParseError, append_json_instruction, parse_json_response

logger = logging.getLogger(__name__)

# 最大追问次数（与 PlanningState.intent_clarification_count 联动）
MAX_CLARIFICATION_COUNT = 2

# LLM 提取意图的 JSON 结构说明（用于 build_json_instruction）
_INTENT_SCHEMA_DESCRIPTION = (
    "包含以下字段的 JSON 对象："
    "origin（出发地，字符串或 null），"
    "city（城市名，字符串，如'上海'），"
    "date（日期 YYYY-MM-DD，字符串），"
    "start_time（开始时间 HH:MM，字符串或 null），"
    "end_time（结束时间 HH:MM，字符串或 null），"
    "time_label（时间段描述如 morning/afternoon/evening，字符串或 null），"
    "participants（参与人员列表，每项包含 type/count/age/relationship/notes），"
    "travel_mode（driving/taxi/public_transit/walking，字符串），"
    "max_distance_km（最远距离限制，数字），"
    "budget_per_person（人均预算，数字或 null），"
    "diet_requirements（饮食要求字符串列表），"
    "soft_preferences（软性偏好字符串列表），"
    "missing_required_slots（缺失的必填槽位名列表，从 [origin, time_window, participants] 中选），"
    "clarification_question（针对缺失槽位的追问，中文字符串，若槽位完整则为 null）"
)

_INTENT_REQUIRED_FIELDS = [
    "origin",
    "city",
    "date",
    "participants",
    "travel_mode",
    "max_distance_km",
    "missing_required_slots",
]

_SYSTEM_PROMPT = """\
你是一个本地活动规划助手的意图解析器。你的任务是从用户输入中提取结构化的规划意图。

提取规则：
1. origin（出发地）：用户提到的出发地点，如"人民广场"、"家"、"公司"。未提及则为 null。
2. city（城市）：活动所在城市，默认"{default_city}"，用户明确提及其他城市时使用用户城市。
3. date（日期）：活动日期（YYYY-MM-DD）。"今天"=当天，"明天"=明天，未提及则用今天的日期。
4. start_time / end_time（HH:MM）：活动时间窗口。"上午"→09:30-14:30，"下午"→14:00-20:00，"晚上"→18:00-22:30，未提及则为 null。
5. participants（人员列表）：
   - 每项含：type（adult/child/elder）、count（数量）、age（年龄或 null）、relationship（关系描述或 null）、notes（备注列表）
   - "老婆/妻子" → adult count=1 relationship="wife"
   - "5岁孩子" → child count=1 age=5 relationship="child"
   - "2男2女" → adult count=2 relationship="male_friends" + adult count=2 relationship="female_friends"
   - 用户本人默认加入：adult count=1 relationship="self"
6. travel_mode："地铁/公交"→public_transit，"打车"→taxi，"开车/驾车"→driving，"走路/步行"→walking，未提及→driving。
7. max_distance_km："附近/不远/别太远"→8.0，否则→12.0。
8. budget_per_person：明确提及金额则填写，否则 null。
9. diet_requirements：如"减肥"→["weight_loss_friendly"]，"素食"→["vegetarian"]，等。
10. soft_preferences：如"child_friendly"、"low_intensity"、"healthy_food"、"group_friendly"等。
11. missing_required_slots：从 ["origin", "time_window", "participants"] 中，列出尚未明确的必填槽位。
    - origin 必填：origin 为 null 时加入
    - time_window 必填：start_time 和 end_time 都为 null 时加入
    - participants 必填：participants 列表为空时加入
12. clarification_question：如果 missing_required_slots 非空，生成一句自然的中文追问，同时询问所有缺失槽位。如果槽位完整则为 null。

当前日期：{today}
"""


class IntentParserNode(BaseNode):
    """
    从自然语言输入中提取结构化规划意图。

    构造函数接收 LLMClient 以便在测试时注入 MockLLMClient。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    @property
    def name(self) -> str:
        return "intent_parser"

    async def run(self, state: PlanningState) -> PlanningState:
        """
        执行意图解析。

        流程：
        1. 调用 LLM 提取结构化意图（含缺失槽位检测）
        2. 如果有缺失必填槽位 且 追问次数 < MAX_CLARIFICATION_COUNT：
           - 记录追问到 state（调用方读取后展示给用户）
           - 计数器 +1，返回
        3. 如果超过追问上限：用默认值填充缺失槽位，继续
        4. 组装 UserIntentSchema，写入 state.intent
        5. 向 state.trace 追加 TraceEvent
        """
        state.trace.append(TraceEvent(
            agent=self.name,
            status="running",
            message="开始解析用户意图…",
        ))

        # 从 origin_location 取 city 作为默认城市（可被用户明确表达覆盖）
        default_city = (
            (state.origin_location or {}).get("city") or "上海"
        )

        try:
            raw_data = await self._call_llm(state.raw_input, default_city=default_city)
        except LLMError as exc:
            logger.warning("intent_parser: LLM 调用失败: %s", exc)
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message=f"LLM 调用失败: {exc}",
            ))
            # LLM 调用失败等同于所有槽位缺失，走默认值路径
            raw_data = _empty_raw_data()
        except LLMParseError as exc:
            logger.warning("intent_parser: LLM 响应解析失败: %s", exc)
            state.trace.append(TraceEvent(
                agent=self.name,
                status="error",
                message=f"LLM 响应解析失败: {exc}",
            ))
            # 解析失败等同于所有槽位缺失，走默认值路径
            raw_data = _empty_raw_data()

        missing_slots: list[str] = raw_data.get("missing_required_slots") or []

        if missing_slots and state.intent_clarification_count < MAX_CLARIFICATION_COUNT:
            # 还有追问机会，记录追问
            clarification = raw_data.get("clarification_question") or _default_clarification(missing_slots)
            state.intent_clarification_count += 1
            # 将追问文本写入专用字段，Orchestrator 读取后清空
            state.pending_clarification = clarification
            state.trace.append(TraceEvent(
                agent=self.name,
                status="done",
                message=f"需要追问用户（#{state.intent_clarification_count}），缺失槽位: {missing_slots}",
            ))
            logger.info(
                "intent_parser: 追问 #%d，缺失槽位: %s",
                state.intent_clarification_count,
                missing_slots,
            )
            return state

        # 槽位完整，或者追问次数已达上限 → 填充默认值后组装
        if missing_slots:
            logger.info(
                "intent_parser: 追问次数已达上限 (%d)，用默认值填充缺失槽位: %s",
                MAX_CLARIFICATION_COUNT,
                missing_slots,
            )
            raw_data = _fill_defaults(raw_data, missing_slots, state.raw_input)

        intent = _build_intent(state.raw_input, raw_data)
        state.intent = intent

        state.trace.append(TraceEvent(
            agent=self.name,
            status="done",
            message=f"意图解析完成: scenario={intent.scenario}, origin={intent.origin}",
        ))
        logger.info("intent_parser: 完成，scenario=%s", intent.scenario)
        return state

    async def _call_llm(self, raw_input: str, default_city: str = "上海") -> dict[str, Any]:
        """调用 LLM 并返回解析后的 dict。使用 run_in_executor 避免阻塞事件循环。

        Args:
            raw_input: 用户原始输入文本。
            default_city: 默认城市，来自 state.origin_location.city（若有），否则为"上海"。
        """
        today = date.today().isoformat()
        system_content = _SYSTEM_PROMPT.format(today=today, default_city=default_city)

        messages = [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=raw_input),
        ]
        messages = append_json_instruction(
            messages,
            schema_description=_INTENT_SCHEMA_DESCRIPTION,
            required_fields=_INTENT_REQUIRED_FIELDS,
        )

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._llm.chat(messages, temperature=0.2, json_mode=True),
        )
        return parse_json_response(response, required_fields=_INTENT_REQUIRED_FIELDS)


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def _build_intent(raw_text: str, data: dict[str, Any]) -> UserIntentSchema:
    """将 LLM 提取的 dict 组装成 UserIntentSchema。"""
    participants = _parse_participants(data.get("participants") or [])
    scenario = _detect_scenario(participants)

    time_window = TimeWindowSchema(
        date=data.get("date") or date.today().isoformat(),
        start=data.get("start_time") or None,
        end=data.get("end_time") or None,
        label=data.get("time_label") or None,
    )

    # 时长推算：基于时间窗口，缺省 4-6h
    duration_min, duration_max = _estimate_duration(
        data.get("start_time"), data.get("end_time")
    )

    travel_mode: TravelMode = _safe_travel_mode(data.get("travel_mode"))
    max_distance_km = float(data.get("max_distance_km") or 12.0)
    budget = data.get("budget_per_person")
    budget_per_person = int(budget) if budget is not None else None

    diet_requirements: list[str] = data.get("diet_requirements") or []
    soft_preferences: list[str] = data.get("soft_preferences") or []

    # 补充 scenario 对应的软性偏好（若 LLM 没提取到）
    soft_preferences = _enrich_soft_preferences(scenario, soft_preferences, diet_requirements)

    return UserIntentSchema(
        raw_text=raw_text,
        city=data.get("city") or "上海",
        origin=data.get("origin") or "当前位置",
        time_window=time_window,
        duration_hours_min=duration_min,
        duration_hours_max=duration_max,
        participants=participants,
        travel_mode=travel_mode,
        max_distance_km=max_distance_km,
        budget_per_person=budget_per_person,
        hard_constraints=["within_time_window", "within_max_distance"],
        soft_preferences=soft_preferences,
        diet_requirements=diet_requirements,
        scenario=scenario,
    )


def _parse_participants(raw_list: list[Any]) -> list[ParticipantSchema]:
    """将 LLM 返回的 participants 列表转换为 ParticipantSchema 列表。"""
    result: list[ParticipantSchema] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        p_type = item.get("type", "adult")
        if p_type not in ("adult", "child", "elder"):
            p_type = "adult"
        count = max(1, int(item.get("count") or 1))
        age_raw = item.get("age")
        age = int(age_raw) if age_raw is not None else None
        result.append(ParticipantSchema(
            type=p_type,
            count=count,
            age=age,
            relationship=item.get("relationship") or None,
            notes=list(item.get("notes") or []),
        ))
    # 如果解析后列表为空，补充一个"本人"
    if not result:
        result.append(ParticipantSchema(type="adult", count=1, relationship="self"))
    return result


def _detect_scenario(participants: list[ParticipantSchema]):
    """
    根据参与人员判断 scenario。

    规则（与 mock_llm_parse_intent 保持一致）：
    - 有 child 参与者 → family_weight_loss_child5
    - 有 4 个以上 adult 且无 child → friends_4_mixed_gender
    - 其他 → family_weight_loss_child5（保守默认）
    """
    has_child = any(p.type == "child" for p in participants)
    total_adults = sum(p.count for p in participants if p.type == "adult")

    if has_child:
        return "family_weight_loss_child5"
    if total_adults >= 4:
        return "friends_4_mixed_gender"
    return "family_weight_loss_child5"


def _estimate_duration(
    start_time: str | None, end_time: str | None
) -> tuple[float, float]:
    """根据时间窗口推算计划时长（小时）。"""
    if start_time and end_time:
        try:
            sh, sm = map(int, start_time.split(":"))
            eh, em = map(int, end_time.split(":"))
            total = (eh * 60 + em) - (sh * 60 + sm)
            if total > 0:
                duration = total / 60
                # 给 min/max 留一点弹性
                return max(0.5, duration - 0.5), duration
        except (ValueError, AttributeError):
            pass
    return 4.0, 6.0


def _safe_travel_mode(raw: Any) -> TravelMode:
    """确保 travel_mode 是合法枚举值，否则回退到 driving。"""
    valid: set[TravelMode] = {"driving", "taxi", "public_transit", "walking"}
    if raw in valid:
        return raw  # type: ignore[return-value]
    return "driving"


def _enrich_soft_preferences(
    scenario: str,
    existing: list[str],
    diet_requirements: list[str],
) -> list[str]:
    """根据 scenario 补充未被 LLM 提取到的常见软性偏好。"""
    prefs = list(existing)
    if scenario == "family_weight_loss_child5":
        for pref in ("child_friendly", "low_intensity"):
            if pref not in prefs:
                prefs.append(pref)
        if "weight_loss_friendly" in diet_requirements and "healthy_food" not in prefs:
            prefs.append("healthy_food")
    elif scenario == "friends_4_mixed_gender":
        for pref in ("group_friendly", "mixed_gender_friendly"):
            if pref not in prefs:
                prefs.append(pref)
    return prefs


def _empty_raw_data() -> dict[str, Any]:
    """LLM 解析完全失败时的空数据骨架。"""
    return {
        "origin": None,
        "city": "上海",
        "date": date.today().isoformat(),
        "start_time": None,
        "end_time": None,
        "time_label": None,
        "participants": [],
        "travel_mode": "driving",
        "max_distance_km": 12.0,
        "budget_per_person": None,
        "diet_requirements": [],
        "soft_preferences": [],
        "missing_required_slots": ["origin", "time_window", "participants"],
        "clarification_question": None,
    }


def _fill_defaults(
    data: dict[str, Any],
    missing_slots: list[str],
    raw_input: str,
) -> dict[str, Any]:
    """
    用合理默认值填充缺失的必填槽位。
    追问次数超限时调用。
    """
    result = dict(data)

    if "origin" in missing_slots:
        result["origin"] = "当前位置"

    if "time_window" in missing_slots:
        # 默认下午场
        result["start_time"] = "14:00"
        result["end_time"] = "20:00"
        result["time_label"] = "afternoon"

    if "participants" in missing_slots:
        # 默认：用户本人（单人）
        result["participants"] = [
            {"type": "adult", "count": 1, "age": None, "relationship": "self", "notes": []}
        ]

    # 清空缺失列表，让后续流程继续
    result["missing_required_slots"] = []
    result["clarification_question"] = None
    return result


def _default_clarification(missing_slots: list[str]) -> str:
    """当 LLM 没有给出追问时的兜底追问文案。"""
    slot_names = {
        "origin": "出发地点",
        "time_window": "活动时间",
        "participants": "参与人员",
    }
    missing_cn = [slot_names.get(s, s) for s in missing_slots]
    return f"还需要了解一下：{'、'.join(missing_cn)}，请补充一下吧～"
