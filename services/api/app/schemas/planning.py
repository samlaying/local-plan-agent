from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ParticipantType = Literal["adult", "child", "elder"]
TravelMode = Literal["driving", "taxi", "public_transit", "walking"]
Scenario = Literal["family_weight_loss_child5", "friends_4_mixed_gender"]
POICategory = Literal["family_activity", "friends_activity", "restaurant"]
PriceLevel = Literal["low", "medium", "high"]
ActionType = Literal[
    "navigation",
    "reservation",
    "queue",
    "ticket",
    "order",
    "message",
    "calendar",
]
ActionStatus = Literal["pending", "needs_confirmation", "mocked", "success", "failed"]


class ParticipantSchema(BaseModel):
    type: ParticipantType
    count: int = Field(ge=1)
    age: int | None = Field(default=None, ge=0)
    relationship: str | None = None
    notes: list[str] = Field(default_factory=list)


class TimeWindowSchema(BaseModel):
    date: str
    start: str | None = None
    end: str | None = None
    label: str | None = None


class UserIntentSchema(BaseModel):
    raw_text: str
    city: str
    origin: str
    time_window: TimeWindowSchema
    duration_hours_min: float = Field(ge=0.5)
    duration_hours_max: float = Field(ge=0.5)
    participants: list[ParticipantSchema]
    travel_mode: TravelMode = "driving"
    max_distance_km: float = Field(ge=0)
    budget_per_person: int | None = Field(default=None, ge=0)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_preferences: list[str] = Field(default_factory=list)
    diet_requirements: list[str] = Field(default_factory=list)
    scenario: Scenario


class BusinessHoursSchema(BaseModel):
    open: str
    close: str
    last_entry: str | None = None
    note: str | None = None


class AudienceFitSchema(BaseModel):
    family: int = Field(ge=0, le=100)
    child_age_5: int = Field(ge=0, le=100)
    weight_loss_friendly: int = Field(ge=0, le=100)
    friends_group: int = Field(ge=0, le=100)
    mixed_gender_group: int = Field(ge=0, le=100)


class QueueInfoSchema(BaseModel):
    wait_minutes: int = Field(ge=0)
    level: Literal["none", "low", "medium", "high"]
    note: str | None = None


class LocationSchema(BaseModel):
    lat: float
    lng: float


class POISchema(BaseModel):
    id: str
    provider: Literal["mock", "amap"] = "mock"
    name: str
    category: POICategory
    subcategory: str
    address: str
    city: str
    distance_km: float = Field(ge=0)
    travel_minutes: int = Field(ge=0)
    price_per_person: int = Field(ge=0)
    price_level: PriceLevel
    rating: float = Field(ge=0, le=5)
    audience_fit: AudienceFitSchema
    business_hours: BusinessHoursSchema
    reservable: bool
    queue: QueueInfoSchema
    recommended_duration_minutes: int = Field(ge=0)
    tags: list[str] = Field(default_factory=list)
    suitable_scenarios: list[Scenario] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)
    location: LocationSchema
    # Optional fields for real-API data; not populated by mock data.
    amap_id: str | None = None


class ItineraryStepSchema(BaseModel):
    id: str
    type: Literal["activity", "meal", "extra", "transit"]
    title: str
    poi_id: str | None = None
    start_time: str
    end_time: str
    duration_minutes: int = Field(ge=0)
    description: str
    fit_reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    action_refs: list[str] = Field(default_factory=list)


class ActionSchema(BaseModel):
    id: str
    plan_id: str
    type: ActionType
    title: str
    provider: Literal["mock", "amap", "system"]
    status: ActionStatus = "pending"
    requires_user_confirmation: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None


class PlanSchema(BaseModel):
    id: str
    title: str
    summary: str
    scenario: Scenario
    total_duration_minutes: int = Field(ge=0)
    estimated_cost_min: int = Field(ge=0)
    estimated_cost_max: int = Field(ge=0)
    currency: Literal["CNY"] = "CNY"
    score: float = Field(ge=0, le=100)
    risk_level: Literal["low", "medium", "high"]
    steps: list[ItineraryStepSchema]
    pois: list[POISchema]
    actions: list[ActionSchema] = Field(default_factory=list)
    fit_summary: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)


class UserProfileSchema(BaseModel):
    session_id: str
    preference_weights: dict[str, float] = Field(default_factory=dict)
    selected_poi_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
