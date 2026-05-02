from datetime import datetime

from fastapi import APIRouter, Query

from app.schemas.city_guide import (
    CityArticleListResponse,
    CityArticleSchema,
    CityEventListResponse,
    CityGuideHomeResponse,
    CityRouteListResponse,
    GeneratePlanFromCityContentRequest,
)
from app.schemas.inspirations import InspirationItemSchema
from app.services.activity_workflow import WorkflowResult
from app.services.city_guide import city_guide_service

router = APIRouter(prefix="/api/city-guide", tags=["city-guide"])


@router.get("/home", response_model=CityGuideHomeResponse)
def get_city_guide_home(
    city: str = Query(default="Shanghai"),
    district: str | None = Query(default=None),
) -> CityGuideHomeResponse:
    return city_guide_service.home(city=city, district=district)


@router.get("/articles", response_model=CityArticleListResponse)
def list_city_articles(
    city: str = Query(default="Shanghai"),
    district: str | None = Query(default=None),
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> CityArticleListResponse:
    return city_guide_service.list_articles(
        city=city,
        district=district,
        category=category,
        tag=tag,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.get("/articles/{article_id}", response_model=CityArticleSchema)
def get_city_article(article_id: str) -> CityArticleSchema:
    return city_guide_service.get_article(article_id)


@router.post("/articles/{article_id}/save-to-inspirations", response_model=InspirationItemSchema)
def save_city_article_to_inspirations(
    article_id: str,
    user_id: str = Query(default="user_demo"),
) -> InspirationItemSchema:
    return city_guide_service.save_article_to_inspirations(article_id, user_id=user_id)


@router.post("/articles/{article_id}/generate-plan", response_model=WorkflowResult)
def generate_plan_from_city_article(
    article_id: str, request: GeneratePlanFromCityContentRequest
) -> WorkflowResult:
    return city_guide_service.generate_plan_from_article(article_id, request)


@router.get("/routes", response_model=CityRouteListResponse)
def list_city_routes(
    city: str = Query(default="Shanghai"),
    district: str | None = Query(default=None),
    route_type: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> CityRouteListResponse:
    return city_guide_service.list_routes(
        city=city,
        district=district,
        route_type=route_type,
        tag=tag,
        page=page,
        page_size=page_size,
    )


@router.post("/routes/{route_id}/generate-plan", response_model=WorkflowResult)
def generate_plan_from_city_route(route_id: str, request: GeneratePlanFromCityContentRequest) -> WorkflowResult:
    return city_guide_service.generate_plan_from_route(route_id, request)


@router.get("/events", response_model=CityEventListResponse)
def list_city_events(
    city: str = Query(default="Shanghai"),
    district: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> CityEventListResponse:
    return city_guide_service.list_events(
        city=city,
        district=district,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
