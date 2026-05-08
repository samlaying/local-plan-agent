from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.repositories.mock_poi_repository import MockPOIRepository
from app.schemas.planning import (
    ActionSchema,
    ItineraryStepSchema,
    ParticipantSchema,
    PlanSchema,
    POISchema,
    TimeWindowSchema,
    UserIntentSchema,
)


class UserLocationSchema(BaseModel):
    city: str = "Shanghai"
    address: str = "Home"
    lat: float | None = None
    lng: float | None = None


class PlanPreviewRequest(BaseModel):
    query: str = Field(min_length=1)
    location: UserLocationSchema


class CandidateSet(BaseModel):
    activities: list[POISchema]
    restaurants: list[POISchema]


class ConstraintCheckResult(BaseModel):
    activities: list[POISchema]
    restaurants: list[POISchema]
    rejected: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowResult(BaseModel):
    intent: UserIntentSchema
    plans: list[PlanSchema]
    rejected_candidates: list[dict[str, Any]]
    trace: list[dict[str, Any]]


def mock_llm_parse_intent(raw_text: str, location: UserLocationSchema) -> UserIntentSchema:
    text = raw_text.lower()
    is_family = any(token in raw_text for token in ["老婆", "孩子", "5岁", "五岁", "亲子"])
    is_friends = any(token in raw_text for token in ["朋友", "聚会", "2男2女", "四人", "4人"])

    if is_family or not is_friends:
        scenario = "family_weight_loss_child5"
        participants = [
            ParticipantSchema(type="adult", count=1, relationship="self"),
            ParticipantSchema(type="adult", count=1, relationship="wife", notes=["weight_loss"]),
            ParticipantSchema(type="child", count=1, age=5, relationship="child"),
        ]
        diet_requirements = ["weight_loss_friendly"] if "减肥" in raw_text else []
        soft_preferences = ["child_friendly", "low_intensity", "healthy_food"]
    else:
        scenario = "friends_4_mixed_gender"
        participants = [
            ParticipantSchema(type="adult", count=2, relationship="male_friends"),
            ParticipantSchema(type="adult", count=2, relationship="female_friends"),
        ]
        diet_requirements = []
        soft_preferences = ["group_friendly", "mixed_gender_friendly", "good_for_chat"]

    if "上午" in raw_text:
        start, end, label = "09:30", "14:30", "morning"
    elif "晚上" in raw_text or "今晚" in raw_text:
        start, end, label = "18:00", "22:30", "evening"
    else:
        start, end, label = "14:00", "20:00", "afternoon"

    max_distance_km = 8.0 if any(token in raw_text for token in ["别太远", "不远", "附近", "近一点"]) else 12.0
    if "地铁" in raw_text:
        travel_mode = "public_transit"
    elif "打车" in raw_text:
        travel_mode = "taxi"
    else:
        travel_mode = "driving"

    return UserIntentSchema(
        raw_text=raw_text,
        city=location.city,
        origin=location.address,
        time_window=TimeWindowSchema(date=date.today().isoformat(), start=start, end=end, label=label),
        duration_hours_min=4,
        duration_hours_max=6,
        participants=participants,
        travel_mode=travel_mode,
        max_distance_km=max_distance_km,
        budget_per_person=None,
        hard_constraints=["within_time_window", "within_max_distance"],
        soft_preferences=soft_preferences,
        diet_requirements=diet_requirements,
        scenario=scenario,
    )


def parse_intent(raw_text: str, location: UserLocationSchema) -> UserIntentSchema:
    return mock_llm_parse_intent(raw_text=raw_text, location=location)


def search_candidates(intent: UserIntentSchema, repository: MockPOIRepository) -> CandidateSet:
    activities = [
        poi
        for poi in repository.list_activities()
        if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
    ]
    restaurants = [
        poi
        for poi in repository.list_restaurants()
        if intent.scenario in poi.suitable_scenarios and poi.city == intent.city
    ]
    return CandidateSet(activities=activities, restaurants=restaurants)


def check_constraints(intent: UserIntentSchema, candidates: CandidateSet) -> ConstraintCheckResult:
    accepted_activities, rejected_activities = _filter_pois(intent, candidates.activities)
    accepted_restaurants, rejected_restaurants = _filter_pois(intent, candidates.restaurants)
    return ConstraintCheckResult(
        activities=accepted_activities,
        restaurants=accepted_restaurants,
        rejected=[*rejected_activities, *rejected_restaurants],
    )


import logging as _logging
_wf_logger = _logging.getLogger(__name__)


def generate_plans(intent: UserIntentSchema, candidates: ConstraintCheckResult) -> list[PlanSchema]:
    ranked_activities = sorted(candidates.activities, key=lambda poi: _poi_score(intent, poi), reverse=True)
    ranked_restaurants = sorted(candidates.restaurants, key=lambda poi: _poi_score(intent, poi), reverse=True)

    # 无餐厅时（include_meal=False 或 fallback 候选池无餐厅）：生成纯活动方案
    if not ranked_restaurants:
        _wf_logger.warning("generate_plans: 无餐厅候选，生成纯活动方案")
        plans: list[PlanSchema] = []
        for index, activity in enumerate(ranked_activities[:3]):
            steps_spec = [
                {
                    "poi": activity,
                    "type": "activity",
                    "duration_minutes": min(activity.recommended_duration_minutes, 150),
                    "description": None,
                }
            ]
            plans.append(_build_plan_from_steps(intent, steps_spec, index + 1))
        return plans

    plans = []
    for index, activity in enumerate(ranked_activities[:3]):
        restaurant = ranked_restaurants[index % len(ranked_restaurants)]
        extra = _pick_extra_activity(intent, ranked_activities, activity, index)
        plans.append(_build_plan(intent, activity, restaurant, extra, index + 1))
    return plans


def critique_plans(intent: UserIntentSchema, plans: list[PlanSchema]) -> list[PlanSchema]:
    critiqued: list[PlanSchema] = []
    for plan in plans:
        risks: list[str] = []
        tradeoffs = list(plan.tradeoffs)

        max_wait = max((poi.queue.wait_minutes for poi in plan.pois), default=0)
        if max_wait >= 25:
            risks.append("Peak queue may affect schedule")
        if any(not poi.reservable and poi.queue.wait_minutes >= 15 for poi in plan.pois):
            risks.append("Some venues do not support reservation")
        if plan.total_duration_minutes > int(intent.duration_hours_max * 60):
            risks.append("Plan is close to or above the requested duration")
        if intent.scenario == "family_weight_loss_child5" and min(
            poi.audience_fit.weight_loss_friendly for poi in plan.pois
        ) < 75:
            risks.append("Some dining or activity choices are not ideal for weight-loss preference")

        risk_level = "high" if len(risks) >= 3 else "medium" if risks else "low"
        score = max(0, plan.score - len(risks) * 6)
        critiqued.append(
            plan.model_copy(
                update={
                    "risk_level": risk_level,
                    "score": score,
                    "tradeoffs": [*tradeoffs, *risks],
                    "steps": [_attach_step_risks(step, risks) for step in plan.steps],
                }
            )
        )
    return critiqued


def generate_actions(intent: UserIntentSchema, plans: list[PlanSchema]) -> list[PlanSchema]:
    updated_plans: list[PlanSchema] = []
    for plan in plans:
        actions: list[ActionSchema] = []
        for poi in plan.pois:
            actions.append(
                ActionSchema(
                    id=f"action_{uuid4().hex[:10]}",
                    plan_id=plan.id,
                    type="navigation",
                    title=f"Navigate to {poi.name}",
                    provider="mock",
                    status="mocked",
                    requires_user_confirmation=False,
                    payload={"poi_id": poi.id, "address": poi.address, "travel_mode": intent.travel_mode},
                )
            )
            if poi.category != "restaurant" and "ticket_required" in poi.tags:
                actions.append(
                    ActionSchema(
                        id=f"action_{uuid4().hex[:10]}",
                        plan_id=plan.id,
                        type="ticket",
                        title=f"Buy tickets for {poi.name}",
                        provider="mock",
                        status="needs_confirmation",
                        payload={"poi_id": poi.id, "unit_price": poi.price_per_person},
                    )
                )
            if poi.reservable:
                actions.append(
                    ActionSchema(
                        id=f"action_{uuid4().hex[:10]}",
                        plan_id=plan.id,
                        type="reservation",
                        title=f"Reserve {poi.name}",
                        provider="mock",
                        status="needs_confirmation",
                        payload={"poi_id": poi.id, "party_size": _participant_count(intent)},
                    )
                )
            elif poi.queue.wait_minutes > 0:
                actions.append(
                    ActionSchema(
                        id=f"action_{uuid4().hex[:10]}",
                        plan_id=plan.id,
                        type="queue",
                        title=f"Take queue number for {poi.name}",
                        provider="mock",
                        status="needs_confirmation",
                        payload={"poi_id": poi.id, "estimated_wait_minutes": poi.queue.wait_minutes},
                    )
                )
        actions.append(
            ActionSchema(
                id=f"action_{uuid4().hex[:10]}",
                plan_id=plan.id,
                type="message",
                title="Send itinerary summary",
                provider="system",
                status="needs_confirmation",
                payload={"channel": "manual_share", "plan_title": plan.title},
            )
        )

        action_refs = [action.id for action in actions]
        steps = [step.model_copy(update={"action_refs": action_refs}) for step in plan.steps]
        updated_plans.append(plan.model_copy(update={"actions": actions, "steps": steps}))
    return updated_plans


def present_result(
    intent: UserIntentSchema,
    plans: list[PlanSchema],
    rejected_candidates: list[dict[str, Any]],
    trace: list[dict[str, Any]],
) -> WorkflowResult:
    return WorkflowResult(intent=intent, plans=plans, rejected_candidates=rejected_candidates, trace=trace)


def run_activity_workflow(
    raw_text: str,
    location: UserLocationSchema,
    repository: MockPOIRepository | None = None,
) -> WorkflowResult:
    repo = repository or MockPOIRepository()
    trace: list[dict[str, Any]] = []

    intent = parse_intent(raw_text, location)
    trace.append({"step": "parse_intent", "scenario": intent.scenario})

    candidates = search_candidates(intent, repo)
    trace.append(
        {
            "step": "search_candidates",
            "activities": len(candidates.activities),
            "restaurants": len(candidates.restaurants),
        }
    )

    checked = check_constraints(intent, candidates)
    trace.append(
        {
            "step": "check_constraints",
            "activities": len(checked.activities),
            "restaurants": len(checked.restaurants),
            "rejected": len(checked.rejected),
        }
    )

    plans = generate_plans(intent, checked)
    trace.append({"step": "generate_plans", "plans": len(plans)})

    plans = critique_plans(intent, plans)
    trace.append({"step": "critique_plans", "risk_levels": [plan.risk_level for plan in plans]})

    plans = generate_actions(intent, plans)
    trace.append({"step": "generate_actions", "actions": sum(len(plan.actions) for plan in plans)})

    result = present_result(intent, plans, checked.rejected, trace)
    trace.append({"step": "present_result", "plans": len(result.plans)})
    return result


def _filter_pois(intent: UserIntentSchema, pois: list[POISchema]) -> tuple[list[POISchema], list[dict[str, Any]]]:
    accepted: list[POISchema] = []
    rejected: list[dict[str, Any]] = []
    for poi in pois:
        reasons: list[str] = []
        if poi.distance_km > intent.max_distance_km:
            reasons.append("distance_exceeded")
        if not _is_open_for_window(poi, intent):
            reasons.append("outside_business_hours")
        if not _matches_audience(intent, poi):
            reasons.append("audience_fit_too_low")
        if intent.budget_per_person is not None and poi.price_per_person > intent.budget_per_person:
            reasons.append("budget_exceeded")

        if reasons:
            rejected.append({"poi_id": poi.id, "name": poi.name, "reasons": reasons})
        else:
            accepted.append(poi)
    return accepted, rejected


def _matches_audience(intent: UserIntentSchema, poi: POISchema) -> bool:
    fit = poi.audience_fit
    if intent.scenario == "family_weight_loss_child5":
        return fit.family >= 70 and fit.child_age_5 >= 70 and fit.weight_loss_friendly >= 65
    return fit.friends_group >= 70 and fit.mixed_gender_group >= 70


def _is_open_for_window(poi: POISchema, intent: UserIntentSchema) -> bool:
    start = _time_to_minutes(intent.time_window.start or "00:00")
    end = _time_to_minutes(intent.time_window.end or "23:59")
    open_at = _time_to_minutes(poi.business_hours.open)
    close_at = _time_to_minutes(poi.business_hours.close)
    return open_at <= start < close_at and open_at < end <= close_at + 90


def _build_plan(
    intent: UserIntentSchema,
    activity: POISchema,
    restaurant: POISchema,
    extra: POISchema | None,
    index: int,
    activity_duration: int | None = None,
    meal_duration: int | None = None,
    extra_duration: int | None = None,
    activity_description: str | None = None,
    meal_description: str | None = None,
    extra_description: str | None = None,
) -> PlanSchema:
    start = _parse_datetime(intent.time_window.date, intent.time_window.start or "14:00")
    steps: list[ItineraryStepSchema] = []

    current = start
    steps.append(_transit_step("transit_start", "Depart from origin", current, activity.travel_minutes))
    current += timedelta(minutes=activity.travel_minutes)

    activity_minutes = activity_duration if activity_duration is not None else min(activity.recommended_duration_minutes, 150)
    steps.append(_poi_step("activity_main", activity, current, activity_minutes, description=activity_description))
    current += timedelta(minutes=activity_minutes)

    if extra is not None:
        steps.append(_transit_step("transit_extra", f"Move to {extra.name}", current, max(8, extra.travel_minutes // 2)))
        current += timedelta(minutes=max(8, extra.travel_minutes // 2))
        extra_minutes = extra_duration if extra_duration is not None else min(extra.recommended_duration_minutes, 75)
        steps.append(_poi_step("extra_activity", extra, current, extra_minutes, step_type="extra", description=extra_description))
        current += timedelta(minutes=extra_minutes)

    steps.append(_transit_step("transit_meal", f"Move to {restaurant.name}", current, max(10, restaurant.travel_minutes // 2)))
    current += timedelta(minutes=max(10, restaurant.travel_minutes // 2))

    meal_minutes = meal_duration if meal_duration is not None else min(restaurant.recommended_duration_minutes, 90)
    steps.append(_poi_step("meal", restaurant, current, meal_minutes, step_type="meal", description=meal_description))
    current += timedelta(minutes=meal_minutes)

    total_minutes = int((current - start).total_seconds() // 60)
    pois = [activity, restaurant] if extra is None else [activity, extra, restaurant]
    cost_min = sum(poi.price_per_person for poi in pois) * _participant_count(intent)
    cost_max = int(cost_min * 1.2)
    score = round(sum(_poi_score(intent, poi) for poi in pois) / len(pois), 1)

    return PlanSchema(
        id=f"plan_{index}",
        title=_plan_title(intent, activity, restaurant, index),
        summary=_plan_summary(intent, activity, restaurant, extra),
        scenario=intent.scenario,
        total_duration_minutes=total_minutes,
        estimated_cost_min=cost_min,
        estimated_cost_max=cost_max,
        score=score,
        risk_level="low",
        steps=steps,
        pois=pois,
        actions=[],
        fit_summary=_fit_summary(intent, activity, restaurant, extra),
        tradeoffs=[],
    )


def _build_plan_from_steps(
    intent: UserIntentSchema,
    steps_spec: list[dict],
    index: int,
) -> PlanSchema:
    """根据 LLM 返回的 steps 列表组装 PlanSchema。

    steps_spec 格式：
        [{"poi": POISchema, "type": "activity"|"meal", "duration_minutes": int, "description": str}, ...]

    时间线构建规则：
    - 第一步前插入从出发地到第一个 POI 的 transit（用 poi.travel_minutes）
    - 后续每步前插入 transit（用 next_poi.travel_minutes // 2，最少 8 分钟）
    """
    start = _parse_datetime(intent.time_window.date, intent.time_window.start or "14:00")
    steps: list[ItineraryStepSchema] = []
    pois: list[POISchema] = []

    current = start
    for step_idx, spec in enumerate(steps_spec):
        poi: POISchema = spec["poi"]
        step_type: str = spec.get("type", "activity")
        duration_minutes: int = spec["duration_minutes"]
        description: str | None = spec.get("description")

        # Transit before each step
        if step_idx == 0:
            transit_minutes = poi.travel_minutes
            transit_title = "Depart from origin"
        else:
            transit_minutes = max(8, poi.travel_minutes // 2)
            transit_title = f"Move to {poi.name}"

        steps.append(_transit_step(
            f"transit_{step_idx}",
            transit_title,
            current,
            transit_minutes,
        ))
        current += timedelta(minutes=transit_minutes)

        steps.append(_poi_step(
            f"{step_type}_{step_idx}",
            poi,
            current,
            duration_minutes,
            step_type=step_type,
            description=description,
        ))
        current += timedelta(minutes=duration_minutes)
        pois.append(poi)

    total_minutes = int((current - start).total_seconds() // 60)
    cost_min = sum(poi.price_per_person for poi in pois) * _participant_count(intent)
    cost_max = int(cost_min * 1.2)
    score = round(sum(_poi_score(intent, poi) for poi in pois) / max(len(pois), 1), 1)

    # Build title and summary from first activity + optional meal
    activity_pois = [s["poi"] for s in steps_spec if s.get("type", "activity") == "activity"]
    meal_pois = [s["poi"] for s in steps_spec if s.get("type") == "meal"]
    main_activity = activity_pois[0] if activity_pois else pois[0]
    restaurant = meal_pois[0] if meal_pois else None

    if intent.scenario == "family_weight_loss_child5":
        title = f"Family plan {index}: {main_activity.name}" + (f" + {restaurant.name}" if restaurant else "")
    else:
        title = f"Friends plan {index}: {main_activity.name}" + (f" + {restaurant.name}" if restaurant else "")

    if restaurant:
        summary = f"{main_activity.name}，然后在{restaurant.name}用餐。"
    else:
        activity_names = "、".join(p.name for p in activity_pois)
        summary = f"{activity_names}，纯活动出行。"

    fit_summary: list[str]
    if intent.scenario == "family_weight_loss_child5":
        fit_summary = ["主要活动适合 5 岁孩子参与。"]
        if restaurant:
            fit_summary.append("餐厅提供适合减脂需求的健康餐食选项。")
    else:
        fit_summary = ["活动适合四人朋友同行。"]
        if restaurant:
            fit_summary.append("餐厅适合混合性别小组用餐和聊天。")

    return PlanSchema(
        id=f"plan_{index}",
        title=title,
        summary=summary,
        scenario=intent.scenario,
        total_duration_minutes=total_minutes,
        estimated_cost_min=cost_min,
        estimated_cost_max=cost_max,
        score=score,
        risk_level="low",
        steps=steps,
        pois=pois,
        actions=[],
        fit_summary=fit_summary,
        tradeoffs=[],
    )


def _pick_extra_activity(
    intent: UserIntentSchema,
    ranked_activities: list[POISchema],
    main_activity: POISchema,
    index: int,
) -> POISchema | None:
    if index == 0:
        return None
    max_extra_duration = 75 if intent.scenario == "family_weight_loss_child5" else 90
    for poi in ranked_activities:
        if poi.id != main_activity.id and poi.recommended_duration_minutes <= max_extra_duration:
            return poi
    return None


def _poi_score(intent: UserIntentSchema, poi: POISchema) -> float:
    fit = poi.audience_fit
    if intent.scenario == "family_weight_loss_child5":
        audience_score = fit.family * 0.35 + fit.child_age_5 * 0.35 + fit.weight_loss_friendly * 0.3
    else:
        audience_score = fit.friends_group * 0.55 + fit.mixed_gender_group * 0.45
    distance_score = max(0, 100 - poi.distance_km * 5)
    queue_score = max(0, 100 - poi.queue.wait_minutes * 2)
    return round(audience_score * 0.55 + distance_score * 0.25 + queue_score * 0.1 + poi.rating * 2, 1)


def _poi_step(
    step_id: str,
    poi: POISchema,
    start: datetime,
    duration_minutes: int,
    step_type: str = "activity",
    description: str | None = None,
) -> ItineraryStepSchema:
    end = start + timedelta(minutes=duration_minutes)
    step_description = description if description else f"{poi.subcategory}; estimated queue {poi.queue.wait_minutes} minutes."
    return ItineraryStepSchema(
        id=step_id,
        type=step_type,
        title=poi.name,
        poi_id=poi.id,
        start_time=start.strftime("%H:%M"),
        end_time=end.strftime("%H:%M"),
        duration_minutes=duration_minutes,
        description=step_description,
        fit_reasons=poi.reasons,
        risks=poi.cautions,
    )


def _transit_step(step_id: str, title: str, start: datetime, duration_minutes: int) -> ItineraryStepSchema:
    end = start + timedelta(minutes=duration_minutes)
    return ItineraryStepSchema(
        id=step_id,
        type="transit",
        title=title,
        start_time=start.strftime("%H:%M"),
        end_time=end.strftime("%H:%M"),
        duration_minutes=duration_minutes,
        description="Estimated local travel time based on mock POI data.",
    )


def _attach_step_risks(step: ItineraryStepSchema, plan_risks: list[str]) -> ItineraryStepSchema:
    if step.type == "transit":
        return step
    return step.model_copy(update={"risks": [*step.risks, *plan_risks]})


def _fit_summary(
    intent: UserIntentSchema,
    activity: POISchema,
    restaurant: POISchema,
    extra: POISchema | None,
) -> list[str]:
    if intent.scenario == "family_weight_loss_child5":
        summary = [
            "Main activity is suitable for a 5-year-old child.",
            "Restaurant has weight-loss-friendly options.",
        ]
    else:
        summary = [
            "Activity supports a four-person friends scenario.",
            "Restaurant works for a mixed-gender group and conversation.",
        ]
    if extra is not None:
        summary.append("Extra activity can be skipped if time or queue pressure increases.")
    return summary


def _plan_title(intent: UserIntentSchema, activity: POISchema, restaurant: POISchema, index: int) -> str:
    if intent.scenario == "family_weight_loss_child5":
        return f"Family plan {index}: {activity.name} + {restaurant.name}"
    return f"Friends plan {index}: {activity.name} + {restaurant.name}"


def _plan_summary(
    intent: UserIntentSchema,
    activity: POISchema,
    restaurant: POISchema,
    extra: POISchema | None,
) -> str:
    base = f"{activity.name} first, then dinner at {restaurant.name}."
    if extra is not None:
        base = f"{activity.name}, optional {extra.name}, then dinner at {restaurant.name}."
    if intent.scenario == "family_weight_loss_child5":
        return f"{base} Prioritizes short travel, child fit, and lighter food."
    return f"{base} Prioritizes group interaction, balanced activity intensity, and easy dining."


def _participant_count(intent: UserIntentSchema) -> int:
    return sum(participant.count for participant in intent.participants)


def _parse_datetime(day: str, time_value: str) -> datetime:
    return datetime.fromisoformat(f"{day}T{time_value}:00")


def _time_to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)
