from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.activity_workflow import UserLocationSchema


CityArticleCategory = Literal[
    "weekly_feature",
    "neighborhood_walk",
    "cafe_bookstore",
    "museum_exhibition",
    "family_day",
    "rainy_day",
    "city_calendar",
]
CityRouteType = Literal["city_walk", "family", "cafe", "museum", "rainy_day", "weekend"]
CityRouteStopType = Literal["activity", "meal", "rest", "viewpoint"]
CityEventCategory = Literal["music", "exhibition", "market", "family", "walk", "other"]


class CityArticleSchema(BaseModel):
    id: str
    city: str
    district: str | None = None
    title: str
    subtitle: str | None = None
    excerpt: str
    content: str
    cover_image_url: str | None = None
    category: CityArticleCategory
    tags: list[str] = Field(default_factory=list)
    reading_minutes: int = Field(ge=1)
    editor_name: str | None = None
    related_poi_ids: list[str] = Field(default_factory=list)
    related_route_ids: list[str] = Field(default_factory=list)
    is_featured: bool = False
    is_published: bool = True
    published_at: datetime
    updated_at: datetime


class CityTopicSchema(BaseModel):
    id: str
    city: str
    title: str
    description: str
    cover_image_url: str | None = None
    article_ids: list[str] = Field(default_factory=list)
    route_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CityRouteStopSchema(BaseModel):
    id: str
    route_id: str
    name: str
    type: CityRouteStopType
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    order_index: int = Field(ge=0)
    description: str | None = None
    recommended_stay_minutes: int | None = Field(default=None, ge=0)


class CityRouteSchema(BaseModel):
    id: str
    city: str
    district: str | None = None
    title: str
    description: str
    cover_image_url: str | None = None
    duration_minutes: int = Field(ge=0)
    distance_km: float = Field(ge=0)
    route_type: CityRouteType
    stops: list[CityRouteStopSchema]
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CityEventSchema(BaseModel):
    id: str
    city: str
    district: str | None = None
    title: str
    description: str | None = None
    location_name: str | None = None
    address: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    category: CityEventCategory
    price_info: str | None = None
    booking_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime


class CityGuideHomeResponse(BaseModel):
    featured_article: CityArticleSchema | None
    weekly_topic: CityTopicSchema | None
    articles: list[CityArticleSchema]
    routes: list[CityRouteSchema]
    events: list[CityEventSchema]
    editor_picks: list[CityArticleSchema]


class CityArticleListResponse(BaseModel):
    items: list[CityArticleSchema]
    total: int
    page: int
    page_size: int


class CityRouteListResponse(BaseModel):
    items: list[CityRouteSchema]
    total: int
    page: int
    page_size: int


class CityEventListResponse(BaseModel):
    items: list[CityEventSchema]
    total: int
    page: int
    page_size: int


class GeneratePlanFromCityContentRequest(BaseModel):
    user_query: str | None = None
    location: UserLocationSchema = Field(default_factory=UserLocationSchema)
