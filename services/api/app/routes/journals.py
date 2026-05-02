from fastapi import APIRouter, Query, Response, status

from app.schemas.journals import (
    CreateJournalFromTripMapRequest,
    JournalListResponse,
    TravelJournalDetailSchema,
    UpdateTravelJournalRequest,
)
from app.services.journals import journal_service

router = APIRouter(prefix="/api/journals", tags=["journals"])


@router.get("", response_model=JournalListResponse)
def list_journals(
    user_id: str = Query(default="user_demo"),
    status_filter: str | None = Query(default=None, alias="status"),
    scene: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    sort: str = Query(default="recent"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=100),
) -> JournalListResponse:
    return journal_service.list_journals(
        user_id=user_id,
        status_filter=status_filter,
        scene=scene,
        tag=tag,
        keyword=keyword,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/{journal_id}", response_model=TravelJournalDetailSchema)
def get_journal(journal_id: str) -> TravelJournalDetailSchema:
    return journal_service.get_detail(journal_id)


@router.post("/from-trip-map", response_model=TravelJournalDetailSchema)
def create_journal_from_trip_map(request: CreateJournalFromTripMapRequest) -> TravelJournalDetailSchema:
    return journal_service.create_from_trip_map(request)


@router.patch("/{journal_id}", response_model=TravelJournalDetailSchema)
def update_journal(journal_id: str, request: UpdateTravelJournalRequest) -> TravelJournalDetailSchema:
    return journal_service.update_journal(journal_id, request)


@router.patch("/{journal_id}/archive", response_model=TravelJournalDetailSchema)
def archive_journal(journal_id: str) -> TravelJournalDetailSchema:
    return journal_service.archive_journal(journal_id)


@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal(journal_id: str) -> Response:
    journal_service.delete_journal(journal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
