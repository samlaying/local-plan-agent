from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from app.schemas.city_guide import (
    CityArticleListResponse,
    CityArticleSchema,
    CityEventListResponse,
    CityEventSchema,
    CityGuideHomeResponse,
    CityRouteListResponse,
    CityRouteSchema,
    CityRouteStopSchema,
    CityTopicSchema,
    GeneratePlanFromCityContentRequest,
)
from app.schemas.inspirations import CreateInspirationRequest, InspirationItemSchema
from app.services.activity_workflow import WorkflowResult, run_activity_workflow
from app.services.inspirations import inspiration_service


class CityGuideService:
    def __init__(self) -> None:
        self._articles: dict[str, CityArticleSchema] = {}
        self._topics: dict[str, CityTopicSchema] = {}
        self._routes: dict[str, CityRouteSchema] = {}
        self._events: dict[str, CityEventSchema] = {}
        self._seed()

    def home(self, *, city: str = "Shanghai", district: str | None = None) -> CityGuideHomeResponse:
        articles = self._filter_articles(city=city, district=district)
        routes = self._filter_routes(city=city, district=district)
        events = self._filter_events(city=city, district=district)
        featured = next((article for article in articles if article.is_featured), articles[0] if articles else None)
        topic = next((topic for topic in self._topics.values() if topic.city == city), None)
        return CityGuideHomeResponse(
            featured_article=featured,
            weekly_topic=topic,
            articles=articles[:6],
            routes=routes[:4],
            events=events[:5],
            editor_picks=[article for article in articles if "编辑推荐" in article.tags][:4],
        )

    def list_articles(
        self,
        *,
        city: str = "Shanghai",
        district: str | None = None,
        category: str | None = None,
        tag: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> CityArticleListResponse:
        items = self._filter_articles(city=city, district=district)
        if category:
            items = [item for item in items if item.category == category]
        if tag:
            items = [item for item in items if tag in item.tags]
        if keyword:
            lowered = keyword.lower()
            items = [
                item
                for item in items
                if lowered in item.title.lower() or lowered in item.excerpt.lower() or lowered in item.content.lower()
            ]
        return CityArticleListResponse(items=_paginate(items, page, page_size), total=len(items), page=page, page_size=page_size)

    def get_article(self, article_id: str) -> CityArticleSchema:
        article = self._articles.get(article_id)
        if article is None or not article.is_published:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City article not found")
        return article

    def save_article_to_inspirations(self, article_id: str, user_id: str = "user_demo") -> InspirationItemSchema:
        article = self.get_article(article_id)
        return inspiration_service.create_item(
            CreateInspirationRequest(
                user_id=user_id,
                type="article",
                title=article.title,
                description=article.excerpt,
                cover_image_url=article.cover_image_url,
                source="city_guide",
                source_id=article.id,
                city=article.city,
                district=article.district,
                tags=article.tags,
                content=article.content,
                payload={"related_poi_ids": article.related_poi_ids, "related_route_ids": article.related_route_ids},
            )
        )

    def generate_plan_from_article(self, article_id: str, request: GeneratePlanFromCityContentRequest) -> WorkflowResult:
        article = self.get_article(article_id)
        query = request.user_query or f"基于城市志文章《{article.title}》生成一个轻松的半日路线"
        return run_activity_workflow(raw_text=query, location=request.location)

    def list_routes(
        self,
        *,
        city: str = "Shanghai",
        district: str | None = None,
        route_type: str | None = None,
        tag: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> CityRouteListResponse:
        items = self._filter_routes(city=city, district=district)
        if route_type:
            items = [item for item in items if item.route_type == route_type]
        if tag:
            items = [item for item in items if tag in item.tags]
        return CityRouteListResponse(items=_paginate(items, page, page_size), total=len(items), page=page, page_size=page_size)

    def generate_plan_from_route(self, route_id: str, request: GeneratePlanFromCityContentRequest) -> WorkflowResult:
        route = self._routes.get(route_id)
        if route is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City route not found")
        stop_names = "、".join(stop.name for stop in route.stops[:3])
        query = request.user_query or f"按「{route.title}」安排半日游，包含 {stop_names}，节奏轻松"
        return run_activity_workflow(raw_text=query, location=request.location)

    def list_events(
        self,
        *,
        city: str = "Shanghai",
        district: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> CityEventListResponse:
        items = self._filter_events(city=city, district=district)
        if date_from:
            items = [item for item in items if item.starts_at >= date_from]
        if date_to:
            items = [item for item in items if item.starts_at <= date_to]
        return CityEventListResponse(items=_paginate(items, page, page_size), total=len(items), page=page, page_size=page_size)

    def _filter_articles(self, *, city: str, district: str | None) -> list[CityArticleSchema]:
        items = [item for item in self._articles.values() if item.city == city and item.is_published]
        if district:
            items = [item for item in items if item.district in {district, None}]
        return sorted(items, key=lambda item: item.published_at, reverse=True)

    def _filter_routes(self, *, city: str, district: str | None) -> list[CityRouteSchema]:
        items = [item for item in self._routes.values() if item.city == city]
        if district:
            items = [item for item in items if item.district in {district, None}]
        return sorted(items, key=lambda item: item.updated_at, reverse=True)

    def _filter_events(self, *, city: str, district: str | None) -> list[CityEventSchema]:
        items = [item for item in self._events.values() if item.city == city]
        if district:
            items = [item for item in items if item.district in {district, None}]
        return sorted(items, key=lambda item: item.starts_at)

    def _seed(self) -> None:
        now = datetime.now(UTC)
        route = CityRouteSchema(
            id="route_xuhui_walk",
            city="Shanghai",
            district="徐汇区",
            title="徐汇梧桐慢行线",
            description="用两到三小时串起街区、公园和咖啡休息点。",
            cover_image_url=_mock_image("xuhui-route"),
            duration_minutes=180,
            distance_km=3.2,
            route_type="city_walk",
            tags=["City Walk", "低强度", "编辑推荐"],
            created_at=now,
            updated_at=now,
            stops=[
                CityRouteStopSchema(
                    id="route_stop_001",
                    route_id="route_xuhui_walk",
                    name="衡复风貌街区",
                    type="viewpoint",
                    address="徐汇区衡山路",
                    lat=31.207,
                    lng=121.445,
                    order_index=0,
                    description="适合慢走和拍街景。",
                    recommended_stay_minutes=45,
                ),
                CityRouteStopSchema(
                    id="route_stop_002",
                    route_id="route_xuhui_walk",
                    name="街角咖啡休息点",
                    type="rest",
                    address="徐汇区乌鲁木齐中路",
                    lat=31.211,
                    lng=121.448,
                    order_index=1,
                    description="中段补水和聊天。",
                    recommended_stay_minutes=50,
                ),
            ],
        )
        article = CityArticleSchema(
            id="article_xuhui_weekly",
            city="Shanghai",
            district="徐汇区",
            title="梧桐浓荫下的慢时光",
            subtitle="徐汇半日散步指南",
            excerpt="一条适合周末下午的低强度街区路线。",
            content="从衡复街区出发，把咖啡、展览和公园休息点串起来，适合亲子或朋友轻松同行。",
            cover_image_url=_mock_image("xuhui-article"),
            category="weekly_feature",
            tags=["编辑推荐", "City Walk", "亲子"],
            reading_minutes=4,
            editor_name="LocalPlan 编辑部",
            related_poi_ids=["poi_xuhui_walk", "poi_cafe_corner"],
            related_route_ids=[route.id],
            is_featured=True,
            published_at=now,
            updated_at=now,
        )
        topic = CityTopicSchema(
            id="topic_weekend_slow_life",
            city="Shanghai",
            title="周末慢生活",
            description="低强度、短距离、可随时停下来的城市半日灵感。",
            cover_image_url=_mock_image("topic-weekend"),
            article_ids=[article.id],
            route_ids=[route.id],
            tags=["周末", "低强度"],
            created_at=now,
            updated_at=now,
        )
        event = CityEventSchema(
            id="event_family_market",
            city="Shanghai",
            district="徐汇区",
            title="周末亲子小市集",
            description="适合作为半日路线的轻量加点。",
            location_name="徐汇滨江",
            address="徐汇区龙腾大道",
            starts_at=now + timedelta(days=3),
            ends_at=now + timedelta(days=3, hours=5),
            category="family",
            price_info="免费入场",
            tags=["亲子", "市集"],
            created_at=now,
        )
        self._routes[route.id] = route
        self._articles[article.id] = article
        self._topics[topic.id] = topic
        self._events[event.id] = event


def _mock_image(seed: str) -> str:
    return f"https://images.unsplash.com/photo-1518005020951-eccb494ad742?auto=format&fit=crop&w=960&q=80&seed={seed}"


def _paginate[T](items: list[T], page: int, page_size: int) -> list[T]:
    start = (page - 1) * page_size
    return items[start : start + page_size]


city_guide_service = CityGuideService()
