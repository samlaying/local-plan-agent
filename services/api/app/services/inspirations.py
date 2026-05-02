from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.inspirations import (
    AddInspirationToCollectionRequest,
    AddInspirationToPlanningDraftRequest,
    CreateInspirationCollectionRequest,
    CreateInspirationFromJournalStopRequest,
    CreateInspirationFromPOIRequest,
    CreateInspirationRequest,
    InspirationCollectionItemSchema,
    InspirationCollectionSchema,
    InspirationItemSchema,
    InspirationListResponse,
    InspirationLocationSchema,
    InspirationStatsSchema,
    PlanningDraftInspirationSchema,
    PlanningDraftSchema,
)
from app.services.journals import journal_service


class InspirationService:
    def __init__(self) -> None:
        self._items: dict[str, InspirationItemSchema] = {}
        self._collections: dict[str, InspirationCollectionSchema] = {}
        self._collection_items: dict[str, list[InspirationCollectionItemSchema]] = {}
        self._drafts: dict[str, PlanningDraftSchema] = {}
        self._seed()

    def list_items(
        self,
        *,
        user_id: str = "user_demo",
        type_filter: str | None = None,
        tag: str | None = None,
        keyword: str | None = None,
        city: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> InspirationListResponse:
        items = [item for item in self._items.values() if item.user_id == user_id and not item.is_archived]
        if type_filter:
            items = [item for item in items if item.type == type_filter]
        if tag:
            items = [item for item in items if tag in item.tags]
        if city:
            items = [item for item in items if item.city == city]
        if keyword:
            lowered = keyword.lower()
            items = [
                item
                for item in items
                if lowered in item.title.lower() or lowered in (item.description or "").lower()
            ]
        items = sorted(items, key=lambda item: item.updated_at, reverse=True)
        stats = InspirationStatsSchema(
            total=len(items),
            collections=len([col for col in self._collections.values() if col.user_id == user_id]),
            visited_places=len([item for item in items if item.type in {"poi", "restaurant", "activity"}]),
        )
        return InspirationListResponse(
            items=_paginate(items, page, page_size),
            total=len(items),
            page=page,
            page_size=page_size,
            stats=stats,
        )

    def create_item(self, request: CreateInspirationRequest) -> InspirationItemSchema:
        now = _now()
        item = InspirationItemSchema(
            id=f"insp_{uuid4().hex[:10]}",
            user_id=request.user_id,
            type=request.type,
            title=request.title,
            description=request.description,
            cover_image_url=request.cover_image_url or _mock_image(request.title),
            source=request.source,
            source_id=request.source_id,
            city=request.city,
            district=request.district,
            location=request.location,
            tags=request.tags,
            content=request.content,
            payload=request.payload,
            group_id=request.group_id,
            created_at=now,
            updated_at=now,
        )
        self._items[item.id] = item
        return item

    def create_from_poi(self, request: CreateInspirationFromPOIRequest) -> InspirationItemSchema:
        poi = request.poi
        location = poi.get("location") or {}
        return self.create_item(
            CreateInspirationRequest(
                user_id=request.user_id,
                type="restaurant" if poi.get("category") == "restaurant" else "poi",
                title=poi.get("name", "未命名地点"),
                description=poi.get("address") or poi.get("subcategory"),
                source=request.source,
                source_id=request.source_id,
                city=poi.get("city", "Shanghai"),
                location=InspirationLocationSchema(
                    lat=location.get("lat", 31.2304),
                    lng=location.get("lng", 121.4737),
                    address=poi.get("address"),
                ),
                tags=poi.get("tags", []),
                payload=poi,
            )
        )

    def create_from_journal_stop(self, request: CreateInspirationFromJournalStopRequest) -> InspirationItemSchema:
        stop = journal_service.get_stop(request.journal_id, request.stop_id)
        return self.create_item(
            CreateInspirationRequest(
                user_id=request.user_id,
                type="poi",
                title=stop.name,
                description=stop.user_note or stop.agent_reason,
                source="journal",
                source_id=request.journal_id,
                city="Shanghai",
                location=(
                    InspirationLocationSchema(lat=stop.lat, lng=stop.lng, address=stop.address)
                    if stop.lat is not None and stop.lng is not None
                    else None
                ),
                tags=["游笺地点", stop.type],
                payload={"journal_id": request.journal_id, "stop_id": request.stop_id},
            )
        )

    def add_to_planning_draft(
        self, inspiration_id: str, request: AddInspirationToPlanningDraftRequest
    ) -> PlanningDraftSchema:
        self._require_item(inspiration_id)
        now = _now()
        draft_id = request.draft_id or f"draft_{uuid4().hex[:10]}"
        draft = self._drafts.get(
            draft_id,
            PlanningDraftSchema(draft_id=draft_id, included_inspirations=[], updated_at=now),
        )
        included = [
            item for item in draft.included_inspirations if item.inspiration_id != inspiration_id
        ]
        included.append(
            PlanningDraftInspirationSchema(inspiration_id=inspiration_id, role=request.role, added_at=now)
        )
        updated = draft.model_copy(update={"included_inspirations": included, "updated_at": now})
        self._drafts[draft_id] = updated
        return updated

    def list_collections(self, *, user_id: str = "user_demo") -> list[InspirationCollectionSchema]:
        return sorted(
            [collection for collection in self._collections.values() if collection.user_id == user_id],
            key=lambda collection: collection.updated_at,
            reverse=True,
        )

    def create_collection(self, request: CreateInspirationCollectionRequest) -> InspirationCollectionSchema:
        now = _now()
        collection = InspirationCollectionSchema(
            id=f"col_{uuid4().hex[:10]}",
            user_id=request.user_id,
            name=request.name,
            description=request.description,
            cover_image_url=request.cover_image_url or _mock_image(request.name),
            item_count=0,
            created_at=now,
            updated_at=now,
        )
        self._collections[collection.id] = collection
        self._collection_items[collection.id] = []
        return collection

    def add_to_collection(
        self, collection_id: str, request: AddInspirationToCollectionRequest
    ) -> InspirationCollectionItemSchema:
        collection = self._require_collection(collection_id)
        self._require_item(request.inspiration_id)
        now = _now()
        existing = self._collection_items.setdefault(collection_id, [])
        for item in existing:
            if item.inspiration_id == request.inspiration_id:
                return item
        link = InspirationCollectionItemSchema(
            id=f"coli_{uuid4().hex[:10]}",
            collection_id=collection_id,
            inspiration_id=request.inspiration_id,
            created_at=now,
        )
        existing.append(link)
        self._collections[collection_id] = collection.model_copy(
            update={"item_count": len(existing), "updated_at": now}
        )
        return link

    def _require_item(self, inspiration_id: str) -> InspirationItemSchema:
        item = self._items.get(inspiration_id)
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspiration not found")
        return item

    def _require_collection(self, collection_id: str) -> InspirationCollectionSchema:
        collection = self._collections.get(collection_id)
        if collection is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspiration collection not found")
        return collection

    def _seed(self) -> None:
        self.create_item(
            CreateInspirationRequest(
                type="note",
                title="雨天也能轻松走完的半日路线",
                description="适合收藏为下一次规划约束。",
                tags=["雨天", "低强度"],
                content="尽量减少室外移动，保留咖啡馆和展览作为锚点。",
            )
        )


def _now() -> datetime:
    return datetime.now(UTC)


def _mock_image(seed: str) -> str:
    return f"https://images.unsplash.com/photo-1494526585095-c41746248156?auto=format&fit=crop&w=960&q=80&seed={seed}"


def _paginate[T](items: list[T], page: int, page_size: int) -> list[T]:
    start = (page - 1) * page_size
    return items[start : start + page_size]


inspiration_service = InspirationService()
