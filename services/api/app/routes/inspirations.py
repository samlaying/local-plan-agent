from fastapi import APIRouter, Query

from app.schemas.inspirations import (
    AddInspirationToCollectionRequest,
    AddInspirationToPlanningDraftRequest,
    CreateInspirationCollectionRequest,
    CreateInspirationFromJournalStopRequest,
    CreateInspirationFromPOIRequest,
    CreateInspirationRequest,
    InspirationCollectionItemSchema,
    InspirationCollectionListResponse,
    InspirationCollectionSchema,
    InspirationItemSchema,
    InspirationListResponse,
    PlanningDraftSchema,
)
from app.services.inspirations import inspiration_service

router = APIRouter(tags=["inspirations"])


@router.get("/api/inspirations", response_model=InspirationListResponse)
def list_inspirations(
    user_id: str = Query(default="user_demo"),
    type_filter: str | None = Query(default=None, alias="type"),
    tag: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    city: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> InspirationListResponse:
    return inspiration_service.list_items(
        user_id=user_id,
        type_filter=type_filter,
        tag=tag,
        keyword=keyword,
        city=city,
        page=page,
        page_size=page_size,
    )


@router.post("/api/inspirations", response_model=InspirationItemSchema)
def create_inspiration(request: CreateInspirationRequest) -> InspirationItemSchema:
    return inspiration_service.create_item(request)


@router.post("/api/inspirations/from-poi", response_model=InspirationItemSchema)
def create_inspiration_from_poi(request: CreateInspirationFromPOIRequest) -> InspirationItemSchema:
    return inspiration_service.create_from_poi(request)


@router.post("/api/inspirations/from-journal-stop", response_model=InspirationItemSchema)
def create_inspiration_from_journal_stop(request: CreateInspirationFromJournalStopRequest) -> InspirationItemSchema:
    return inspiration_service.create_from_journal_stop(request)


@router.post("/api/inspirations/{inspiration_id}/add-to-planning-draft", response_model=PlanningDraftSchema)
def add_inspiration_to_planning_draft(
    inspiration_id: str, request: AddInspirationToPlanningDraftRequest
) -> PlanningDraftSchema:
    return inspiration_service.add_to_planning_draft(inspiration_id, request)


@router.get("/api/inspiration-collections", response_model=InspirationCollectionListResponse)
def list_inspiration_collections(user_id: str = Query(default="user_demo")) -> InspirationCollectionListResponse:
    items = inspiration_service.list_collections(user_id=user_id)
    return InspirationCollectionListResponse(items=items, total=len(items))


@router.post("/api/inspiration-collections", response_model=InspirationCollectionSchema)
def create_inspiration_collection(request: CreateInspirationCollectionRequest) -> InspirationCollectionSchema:
    return inspiration_service.create_collection(request)


@router.post("/api/inspiration-collections/{collection_id}/items", response_model=InspirationCollectionItemSchema)
def add_inspiration_to_collection(
    collection_id: str, request: AddInspirationToCollectionRequest
) -> InspirationCollectionItemSchema:
    return inspiration_service.add_to_collection(collection_id, request)
