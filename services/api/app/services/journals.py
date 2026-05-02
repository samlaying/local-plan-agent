from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status

from app.schemas.collaboration import GroupMemberSchema, MapStopSchema
from app.schemas.journals import (
    CreateJournalFromTripMapRequest,
    JournalListResponse,
    JournalPhotoSchema,
    JournalStopSchema,
    TravelJournalDetailSchema,
    TravelJournalSchema,
    UpdateTravelJournalRequest,
)
from app.services.collaboration import collaboration_service, timeline_service, trip_map_service


class JournalService:
    def __init__(self) -> None:
        self._journals: dict[str, TravelJournalSchema] = {}
        self._stops_by_journal: dict[str, list[JournalStopSchema]] = {}
        self._photos_by_journal: dict[str, list[JournalPhotoSchema]] = {}

    def list_journals(
        self,
        *,
        user_id: str = "user_demo",
        status_filter: str | None = None,
        scene: str | None = None,
        tag: str | None = None,
        keyword: str | None = None,
        sort: str = "recent",
        page: int = 1,
        page_size: int = 12,
    ) -> JournalListResponse:
        items = [journal for journal in self._journals.values() if journal.user_id == user_id]
        if status_filter:
            items = [journal for journal in items if journal.status == status_filter]
        if scene:
            items = [journal for journal in items if journal.scene == scene]
        if tag:
            items = [journal for journal in items if tag in journal.tags]
        if keyword:
            lowered = keyword.lower()
            items = [
                journal
                for journal in items
                if lowered in journal.title.lower() or lowered in (journal.summary or "").lower()
            ]
        reverse = sort != "oldest"
        items = sorted(items, key=lambda journal: journal.updated_at, reverse=reverse)
        total = len(items)
        return JournalListResponse(items=_paginate(items, page, page_size), total=total, page=page, page_size=page_size)

    def get_detail(self, journal_id: str) -> TravelJournalDetailSchema:
        journal = self._require_journal(journal_id)
        trip_map = None
        plan = None
        timeline = []
        companions: list[GroupMemberSchema] = []
        if journal.source_trip_map_id:
            trip_map = trip_map_service.get_snapshot(journal.source_trip_map_id)
            timeline = timeline_service.list_events(plan_id=trip_map.trip_map.plan_id)
        if trip_map is not None:
            plan = collaboration_service.find_plan_by_id(trip_map.trip_map.plan_id)
        if journal.source_group_id:
            companions = collaboration_service.list_group_members(journal.source_group_id)
        return TravelJournalDetailSchema(
            journal=journal,
            plan=plan,
            trip_map=trip_map,
            stops=self._stops_by_journal.get(journal.id, []),
            photos=self._photos_by_journal.get(journal.id, []),
            timeline=timeline,
            companions=companions,
        )

    def create_from_trip_map(self, request: CreateJournalFromTripMapRequest) -> TravelJournalDetailSchema:
        snapshot = trip_map_service.get_snapshot(request.trip_map_id)
        now = _now()
        journal_id = f"journal_{uuid4().hex[:10]}"
        stops = [self._journal_stop_from_map_stop(journal_id, stop, now) for stop in snapshot.stops]
        photos = self._mock_photos(journal_id, stops, now) if request.save_photos else []
        title = request.title or self._default_title(snapshot.stops)
        journal = TravelJournalSchema(
            id=journal_id,
            user_id=request.user_id,
            title=title,
            subtitle="从今日足迹保存",
            cover_image_url=photos[0].url if photos else _mock_image("journal-cover"),
            source_plan_id=snapshot.trip_map.plan_id,
            source_trip_map_id=snapshot.trip_map.id,
            status="completed",
            scene="family",
            city="Shanghai",
            started_at=now,
            ended_at=now,
            total_duration_minutes=snapshot.trip_map.total_duration_minutes,
            total_distance_meters=snapshot.trip_map.total_distance_meters,
            stop_count=len(stops),
            photo_count=len(photos),
            tags=self._default_tags(snapshot.stops),
            summary=f"保存了 {len(stops)} 个停靠点，总路程约 {round(snapshot.trip_map.total_distance_meters / 1000, 1)} 公里。",
            agent_review="这是一条从已确认路线沉淀下来的半日行程记录，可继续补充照片和同行反馈。",
            created_at=now,
            updated_at=now,
        )
        self._journals[journal.id] = journal
        self._stops_by_journal[journal.id] = stops
        self._photos_by_journal[journal.id] = photos
        return self.get_detail(journal.id)

    def update_journal(self, journal_id: str, request: UpdateTravelJournalRequest) -> TravelJournalDetailSchema:
        journal = self._require_journal(journal_id)
        updates = request.model_dump(exclude_unset=True, exclude_none=True)
        updates["updated_at"] = _now()
        self._journals[journal_id] = journal.model_copy(update=updates)
        return self.get_detail(journal_id)

    def archive_journal(self, journal_id: str) -> TravelJournalDetailSchema:
        journal = self._require_journal(journal_id)
        self._journals[journal_id] = journal.model_copy(update={"status": "archived", "updated_at": _now()})
        return self.get_detail(journal_id)

    def delete_journal(self, journal_id: str) -> None:
        self._require_journal(journal_id)
        del self._journals[journal_id]
        self._stops_by_journal.pop(journal_id, None)
        self._photos_by_journal.pop(journal_id, None)

    def get_stop(self, journal_id: str, stop_id: str) -> JournalStopSchema:
        self._require_journal(journal_id)
        for stop in self._stops_by_journal.get(journal_id, []):
            if stop.id == stop_id:
                return stop
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal stop not found")

    def _require_journal(self, journal_id: str) -> TravelJournalSchema:
        journal = self._journals.get(journal_id)
        if journal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Travel journal not found")
        return journal

    def _journal_stop_from_map_stop(self, journal_id: str, stop: MapStopSchema, now: datetime) -> JournalStopSchema:
        return JournalStopSchema(
            id=f"jstop_{uuid4().hex[:10]}",
            journal_id=journal_id,
            source_stop_id=stop.id,
            poi_id=stop.poi_id,
            name=stop.name,
            type=stop.type,
            lat=stop.location.lat,
            lng=stop.location.lng,
            planned_arrival_time=stop.planned_arrival_time,
            planned_leave_time=stop.planned_leave_time,
            estimated_stay_minutes=stop.estimated_stay_minutes,
            status="visited" if stop.status in {"arrived", "completed"} else "planned",
            agent_reason="; ".join(stop.notes) if stop.notes else None,
            created_at=now,
        )

    def _mock_photos(self, journal_id: str, stops: list[JournalStopSchema], now: datetime) -> list[JournalPhotoSchema]:
        return [
            JournalPhotoSchema(
                id=f"photo_{uuid4().hex[:10]}",
                journal_id=journal_id,
                stop_id=stop.id,
                url=_mock_image(stop.name),
                thumbnail_url=_mock_image(f"thumb-{stop.name}"),
                caption=stop.name,
                source="mock",
                created_at=now,
            )
            for stop in stops[:3]
            if stop.type not in {"origin", "destination"}
        ]

    def _default_title(self, stops: list[MapStopSchema]) -> str:
        names = [stop.name for stop in stops if stop.type not in {"origin", "destination"}]
        return " · ".join(names[:2]) if names else "半日游笺"

    def _default_tags(self, stops: list[MapStopSchema]) -> list[str]:
        tags = ["半日游", "今日足迹"]
        if any(stop.type == "meal" for stop in stops):
            tags.append("餐食")
        if any(stop.type == "activity" for stop in stops):
            tags.append("City Walk")
        return tags


journal_service = JournalService()


def _now() -> datetime:
    return datetime.now(UTC)


def _mock_image(seed: str) -> str:
    return f"https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=960&q=80&seed={seed}"


def _paginate[T](items: list[T], page: int, page_size: int) -> list[T]:
    start = (page - 1) * page_size
    return items[start : start + page_size]
