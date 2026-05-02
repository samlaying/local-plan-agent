from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


InspirationType = Literal["poi", "route", "quote", "photo", "article", "restaurant", "activity", "map", "note"]
InspirationSource = Literal["plan", "journal", "city_guide", "manual", "external", "companion_feedback"]
PlanningDraftRole = Literal["must_include", "nice_to_have", "avoid", "reference"]


class InspirationLocationSchema(BaseModel):
    lat: float
    lng: float
    address: str | None = None


class InspirationItemSchema(BaseModel):
    id: str
    user_id: str
    type: InspirationType
    title: str
    description: str | None = None
    cover_image_url: str | None = None
    source: InspirationSource = "manual"
    source_id: str | None = None
    city: str
    district: str | None = None
    location: InspirationLocationSchema | None = None
    tags: list[str] = Field(default_factory=list)
    content: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    group_id: str | None = None
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime


class InspirationCollectionSchema(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None = None
    cover_image_url: str | None = None
    item_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class InspirationCollectionItemSchema(BaseModel):
    id: str
    collection_id: str
    inspiration_id: str
    created_at: datetime


class InspirationStatsSchema(BaseModel):
    total: int
    collections: int
    visited_places: int


class InspirationListResponse(BaseModel):
    items: list[InspirationItemSchema]
    total: int
    page: int
    page_size: int
    stats: InspirationStatsSchema


class InspirationCollectionListResponse(BaseModel):
    items: list[InspirationCollectionSchema]
    total: int


class CreateInspirationRequest(BaseModel):
    user_id: str = "user_demo"
    type: InspirationType
    title: str
    description: str | None = None
    cover_image_url: str | None = None
    source: InspirationSource = "manual"
    source_id: str | None = None
    city: str = "Shanghai"
    district: str | None = None
    location: InspirationLocationSchema | None = None
    tags: list[str] = Field(default_factory=list)
    content: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    group_id: str | None = None


class CreateInspirationFromPOIRequest(BaseModel):
    user_id: str = "user_demo"
    poi: dict[str, Any]
    source: InspirationSource = "plan"
    source_id: str | None = None


class CreateInspirationFromJournalStopRequest(BaseModel):
    user_id: str = "user_demo"
    journal_id: str
    stop_id: str


class AddInspirationToPlanningDraftRequest(BaseModel):
    draft_id: str | None = None
    role: PlanningDraftRole = "must_include"


class PlanningDraftInspirationSchema(BaseModel):
    inspiration_id: str
    role: PlanningDraftRole
    added_at: datetime


class PlanningDraftSchema(BaseModel):
    draft_id: str
    included_inspirations: list[PlanningDraftInspirationSchema]
    updated_at: datetime


class CreateInspirationCollectionRequest(BaseModel):
    user_id: str = "user_demo"
    name: str
    description: str | None = None
    cover_image_url: str | None = None


class AddInspirationToCollectionRequest(BaseModel):
    inspiration_id: str
