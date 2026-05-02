from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.collaboration import GroupMemberSchema, TimelineEventSchema, TripMapSnapshotSchema
from app.schemas.planning import PlanSchema


JournalStatus = Literal["draft", "planned", "ongoing", "completed", "archived"]
JournalScene = Literal["family", "friends", "couple", "solo", "team"]
JournalStopType = Literal["origin", "activity", "meal", "rest", "destination"]
JournalStopStatus = Literal["planned", "visited", "skipped"]
JournalPhotoSource = Literal["mock", "upload", "generated", "external"]


class TravelJournalSchema(BaseModel):
    id: str
    user_id: str
    title: str
    subtitle: str | None = None
    cover_image_url: str | None = None
    source_plan_id: str | None = None
    source_trip_map_id: str | None = None
    source_group_id: str | None = None
    status: JournalStatus = "completed"
    scene: JournalScene = "family"
    city: str
    district: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    total_duration_minutes: int | None = Field(default=None, ge=0)
    total_distance_meters: int | None = Field(default=None, ge=0)
    stop_count: int = Field(ge=0)
    photo_count: int = Field(ge=0)
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    is_public: bool = False
    summary: str | None = None
    agent_review: str | None = None
    created_at: datetime
    updated_at: datetime


class JournalStopSchema(BaseModel):
    id: str
    journal_id: str
    source_stop_id: str | None = None
    poi_id: str | None = None
    name: str
    type: JournalStopType
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    planned_arrival_time: str | None = None
    planned_leave_time: str | None = None
    actual_arrival_time: str | None = None
    actual_leave_time: str | None = None
    estimated_stay_minutes: int | None = Field(default=None, ge=0)
    actual_stay_minutes: int | None = Field(default=None, ge=0)
    status: JournalStopStatus = "planned"
    agent_reason: str | None = None
    user_note: str | None = None
    created_at: datetime


class JournalPhotoSchema(BaseModel):
    id: str
    journal_id: str
    stop_id: str | None = None
    url: str
    thumbnail_url: str | None = None
    caption: str | None = None
    taken_at: datetime | None = None
    source: JournalPhotoSource = "mock"
    created_at: datetime


class TravelJournalDetailSchema(BaseModel):
    journal: TravelJournalSchema
    plan: PlanSchema | None = None
    trip_map: TripMapSnapshotSchema | None = None
    stops: list[JournalStopSchema]
    photos: list[JournalPhotoSchema]
    timeline: list[TimelineEventSchema]
    companions: list[GroupMemberSchema]


class JournalListResponse(BaseModel):
    items: list[TravelJournalSchema]
    total: int
    page: int
    page_size: int


class CreateJournalFromTripMapRequest(BaseModel):
    trip_map_id: str
    user_id: str = "user_demo"
    title: str | None = None
    save_photos: bool = True


class UpdateTravelJournalRequest(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    is_favorite: bool | None = None
    is_public: bool | None = None
    status: JournalStatus | None = None
