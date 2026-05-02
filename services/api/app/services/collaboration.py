from __future__ import annotations

from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import HTTPException, status

from services.api.app.schemas.collaboration import (
    ActivityGroupSchema,
    AddCommentRequest,
    AddVoteRequest,
    CreateGroupRequest,
    CreateShareLinkRequest,
    CreateTripMapRequest,
    GroupCommentSchema,
    GroupFeedbackSummarySchema,
    GroupMemberSchema,
    GroupSnapshotSchema,
    MapStopSchema,
    PlanVoteSchema,
    RouteMode,
    RouteSegmentSchema,
    ShareLinkSchema,
    SharePageSnapshotSchema,
    TimelineActorType,
    TimelineEventSchema,
    TimelineEventType,
    TripMapSchema,
    TripMapSnapshotSchema,
    UpdateMapStopStatusRequest,
)
from services.api.app.schemas.planning import ItineraryStepSchema, LocationSchema, PlanSchema, POISchema


class TimelineService:
    def __init__(self) -> None:
        self._events: dict[str, TimelineEventSchema] = {}

    def record(
        self,
        *,
        plan_id: str,
        event_type: TimelineEventType,
        actor_type: TimelineActorType,
        group_id: str | None = None,
        actor_id: str | None = None,
        event_data: dict | None = None,
    ) -> TimelineEventSchema:
        event = TimelineEventSchema(
            id=f"evt_{uuid4().hex[:12]}",
            plan_id=plan_id,
            group_id=group_id,
            actor_type=actor_type,
            actor_id=actor_id,
            event_type=event_type,
            event_data=event_data or {},
            created_at=_now(),
        )
        self._events[event.id] = event
        return event

    def list_events(self, *, plan_id: str | None = None, group_id: str | None = None) -> list[TimelineEventSchema]:
        events = list(self._events.values())
        if plan_id is not None:
            events = [event for event in events if event.plan_id == plan_id]
        if group_id is not None:
            events = [event for event in events if event.group_id == group_id]
        return sorted(events, key=lambda event: event.created_at)


class MockMapProvider:
    provider_name = "mock"

    def build_segment(
        self,
        *,
        trip_map_id: str,
        from_stop: MapStopSchema,
        to_stop: MapStopSchema,
        route_mode: RouteMode,
    ) -> RouteSegmentSchema:
        distance_meters = _distance_meters(from_stop.location, to_stop.location)
        speed_kmh = {"walking": 4.5, "transit": 22, "taxi": 28, "driving": 30}[route_mode]
        duration_minutes = max(3, round(distance_meters / 1000 / speed_kmh * 60))
        return RouteSegmentSchema(
            id=f"seg_{uuid4().hex[:10]}",
            trip_map_id=trip_map_id,
            from_stop_id=from_stop.id,
            to_stop_id=to_stop.id,
            distance_meters=distance_meters,
            duration_minutes=duration_minutes,
            polyline=self._mock_polyline(from_stop.location, to_stop.location),
            route_mode=route_mode,
            traffic_status="unknown",
            provider_raw={"source": "haversine_mock"},
            created_at=_now(),
        )

    def _mock_polyline(self, start: LocationSchema, end: LocationSchema) -> str:
        mid = LocationSchema(lat=(start.lat + end.lat) / 2, lng=(start.lng + end.lng) / 2)
        return f"{start.lat:.6f},{start.lng:.6f};{mid.lat:.6f},{mid.lng:.6f};{end.lat:.6f},{end.lng:.6f}"


class TripMapService:
    def __init__(self, timeline_service: TimelineService, map_provider: MockMapProvider | None = None) -> None:
        self._timeline = timeline_service
        self._provider = map_provider or MockMapProvider()
        self._maps: dict[str, TripMapSchema] = {}
        self._stops_by_map: dict[str, list[MapStopSchema]] = {}
        self._segments_by_map: dict[str, list[RouteSegmentSchema]] = {}

    def create_from_plan(self, request: CreateTripMapRequest) -> TripMapSnapshotSchema:
        now = _now()
        trip_map_id = f"map_{uuid4().hex[:10]}"
        stops = self._build_stops(trip_map_id=trip_map_id, request=request, now=now)
        segments = [
            self._provider.build_segment(
                trip_map_id=trip_map_id,
                from_stop=from_stop,
                to_stop=to_stop,
                route_mode=request.route_mode,
            )
            for from_stop, to_stop in zip(stops, stops[1:])
        ]
        trip_map = TripMapSchema(
            id=trip_map_id,
            plan_id=request.plan.id,
            user_id=request.user_id,
            start_location=request.start_location,
            end_location=request.end_location or stops[-1].location,
            route_mode=request.route_mode,
            total_distance_meters=sum(segment.distance_meters for segment in segments),
            total_duration_minutes=sum(segment.duration_minutes for segment in segments),
            status="planned",
            map_provider=self._provider.provider_name,
            created_at=now,
            updated_at=now,
        )
        self._maps[trip_map.id] = trip_map
        self._stops_by_map[trip_map.id] = stops
        self._segments_by_map[trip_map.id] = segments
        self._timeline.record(
            plan_id=request.plan.id,
            actor_type="system",
            actor_id=request.user_id,
            event_type="map_updated",
            event_data={"trip_map_id": trip_map.id, "stop_count": len(stops), "segment_count": len(segments)},
        )
        return self.get_snapshot(trip_map.id)

    def get_snapshot(self, trip_map_id: str) -> TripMapSnapshotSchema:
        trip_map = self._maps.get(trip_map_id)
        if trip_map is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip map not found")
        return TripMapSnapshotSchema(
            trip_map=trip_map,
            stops=self._stops_by_map[trip_map_id],
            route_segments=self._segments_by_map[trip_map_id],
        )

    def update_stop_status(self, stop_id: str, request: UpdateMapStopStatusRequest) -> MapStopSchema:
        for trip_map_id, stops in self._stops_by_map.items():
            for index, stop in enumerate(stops):
                if stop.id != stop_id:
                    continue
                updated = stop.model_copy(update={"status": request.status, "updated_at": _now()})
                stops[index] = updated
                trip_map = self._maps[trip_map_id]
                self._maps[trip_map_id] = trip_map.model_copy(update={"updated_at": _now()})
                self._timeline.record(
                    plan_id=updated.plan_id,
                    actor_type="system",
                    event_type="map_updated",
                    event_data={"stop_id": stop_id, "status": request.status},
                )
                return updated
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Map stop not found")

    def _build_stops(self, *, trip_map_id: str, request: CreateTripMapRequest, now: datetime) -> list[MapStopSchema]:
        stops = [
            MapStopSchema(
                id=f"stop_{uuid4().hex[:10]}",
                trip_map_id=trip_map_id,
                plan_id=request.plan.id,
                name="Origin",
                type="origin",
                location=request.start_location,
                order_index=0,
                planned_arrival_time=request.plan.steps[0].start_time if request.plan.steps else "",
                planned_leave_time=request.plan.steps[0].end_time if request.plan.steps else "",
                estimated_stay_minutes=0,
                status="pending",
                notes=["Generated from user origin"],
                created_at=now,
                updated_at=now,
            )
        ]
        pois_by_id = {poi.id: poi for poi in request.plan.pois}
        poi_steps = [step for step in request.plan.steps if step.poi_id and step.poi_id in pois_by_id]
        for index, step in enumerate(poi_steps, start=1):
            poi = pois_by_id[step.poi_id or ""]
            stops.append(self._stop_from_step(trip_map_id, request.plan.id, step, poi, index, now))
        if request.end_location is not None:
            stops.append(
                MapStopSchema(
                    id=f"stop_{uuid4().hex[:10]}",
                    trip_map_id=trip_map_id,
                    plan_id=request.plan.id,
                    name="Destination",
                    type="destination",
                    location=request.end_location,
                    order_index=len(stops),
                    planned_arrival_time=poi_steps[-1].end_time if poi_steps else "",
                    planned_leave_time=poi_steps[-1].end_time if poi_steps else "",
                    estimated_stay_minutes=0,
                    status="pending",
                    notes=["Generated from requested destination"],
                    created_at=now,
                    updated_at=now,
                )
            )
        return stops

    def _stop_from_step(
        self,
        trip_map_id: str,
        plan_id: str,
        step: ItineraryStepSchema,
        poi: POISchema,
        order_index: int,
        now: datetime,
    ) -> MapStopSchema:
        stop_type = "meal" if step.type == "meal" else "activity" if step.type in {"activity", "extra"} else "rest"
        return MapStopSchema(
            id=f"stop_{uuid4().hex[:10]}",
            trip_map_id=trip_map_id,
            plan_id=plan_id,
            poi_id=poi.id,
            name=poi.name,
            type=stop_type,
            location=poi.location,
            order_index=order_index,
            planned_arrival_time=step.start_time,
            planned_leave_time=step.end_time,
            estimated_stay_minutes=step.duration_minutes,
            status="pending",
            notes=[*step.fit_reasons, *step.risks],
            created_at=now,
            updated_at=now,
        )


class CollaborationService:
    def __init__(self, timeline_service: TimelineService) -> None:
        self._timeline = timeline_service
        self._groups: dict[str, ActivityGroupSchema] = {}
        self._plans_by_group: dict[str, PlanSchema] = {}
        self._members_by_group: dict[str, list[GroupMemberSchema]] = {}
        self._share_links_by_token: dict[str, ShareLinkSchema] = {}
        self._share_tokens_by_group: dict[str, list[str]] = {}
        self._comments_by_group: dict[str, list[GroupCommentSchema]] = {}
        self._votes_by_group: dict[str, list[PlanVoteSchema]] = {}

    def create_group(self, request: CreateGroupRequest) -> GroupSnapshotSchema:
        now = _now()
        group = ActivityGroupSchema(
            id=f"grp_{uuid4().hex[:10]}",
            owner_id=request.owner_id,
            plan_id=request.plan.id,
            name=request.name,
            scene=request.scene,
            status="active",
            share_code=token_urlsafe(5).replace("-", "").replace("_", "").upper()[:8],
            created_at=now,
            updated_at=now,
        )
        owner_member = GroupMemberSchema(
            id=f"mem_{uuid4().hex[:10]}",
            group_id=group.id,
            user_id=request.owner_id,
            role="owner",
            status="joined",
            last_seen_at=now,
            created_at=now,
        )
        self._groups[group.id] = group
        self._plans_by_group[group.id] = request.plan
        self._members_by_group[group.id] = [owner_member]
        self._comments_by_group[group.id] = []
        self._votes_by_group[group.id] = []
        share_link = self.create_share_link(group.id, CreateShareLinkRequest(permission=request.share_permission))
        self._timeline.record(
            plan_id=group.plan_id,
            group_id=group.id,
            actor_type="user",
            actor_id=request.owner_id,
            event_type="plan_shared",
            event_data={"share_token": share_link.token, "permission": share_link.permission},
        )
        return GroupSnapshotSchema(group=group, owner_member=owner_member, share_link=share_link)

    def create_share_link(self, group_id: str, request: CreateShareLinkRequest) -> ShareLinkSchema:
        group = self._require_group(group_id)
        share_link = ShareLinkSchema(
            id=f"shr_{uuid4().hex[:10]}",
            group_id=group.id,
            plan_id=group.plan_id,
            token=f"trip_{token_urlsafe(10)}",
            permission=request.permission,
            expires_at=request.expires_at,
            open_count=0,
            created_at=_now(),
        )
        self._share_links_by_token[share_link.token] = share_link
        self._share_tokens_by_group.setdefault(group.id, []).append(share_link.token)
        return share_link

    def get_share_page(self, token: str) -> SharePageSnapshotSchema:
        share_link = self._require_share_link(token)
        updated_link = share_link.model_copy(update={"open_count": share_link.open_count + 1})
        self._share_links_by_token[token] = updated_link
        group = self._require_group(updated_link.group_id)
        return SharePageSnapshotSchema(
            group=group,
            share_link=updated_link,
            plan=self._plans_by_group[group.id],
            members=self._members_by_group[group.id],
            comments=self._comments_by_group[group.id],
            votes=self._votes_by_group[group.id],
            timeline=self._timeline.list_events(plan_id=group.plan_id, group_id=group.id),
        )

    def join_share(self, token: str, guest_name: str) -> GroupMemberSchema:
        share_link = self._require_share_link(token)
        now = _now()
        member = GroupMemberSchema(
            id=f"mem_{uuid4().hex[:10]}",
            group_id=share_link.group_id,
            guest_name=guest_name,
            guest_avatar_seed=token_urlsafe(4),
            role="guest",
            status="joined",
            last_seen_at=now,
            created_at=now,
        )
        self._members_by_group[share_link.group_id].append(member)
        self._timeline.record(
            plan_id=share_link.plan_id,
            group_id=share_link.group_id,
            actor_type="member",
            actor_id=member.id,
            event_type="member_joined",
            event_data={"guest_name": guest_name},
        )
        return member

    def add_comment(self, group_id: str, request: AddCommentRequest) -> GroupCommentSchema:
        group = self._require_group(group_id)
        self._require_member(group_id, request.member_id)
        comment = GroupCommentSchema(
            id=f"cmt_{uuid4().hex[:10]}",
            group_id=group.id,
            plan_id=group.plan_id,
            member_id=request.member_id,
            content=request.content,
            target_type=request.target_type,
            target_id=request.target_id,
            created_at=_now(),
        )
        self._comments_by_group[group.id].append(comment)
        self._timeline.record(
            plan_id=group.plan_id,
            group_id=group.id,
            actor_type="member",
            actor_id=request.member_id,
            event_type="comment_added",
            event_data={"content": request.content, "target_type": request.target_type, "target_id": request.target_id},
        )
        return comment

    def add_vote(self, group_id: str, request: AddVoteRequest) -> PlanVoteSchema:
        group = self._require_group(group_id)
        self._require_member(group_id, request.member_id)
        vote = PlanVoteSchema(
            id=f"vote_{uuid4().hex[:10]}",
            group_id=group.id,
            plan_id=group.plan_id,
            member_id=request.member_id,
            vote_type=request.vote_type,
            comment=request.comment,
            created_at=_now(),
        )
        self._votes_by_group[group.id].append(vote)
        self._timeline.record(
            plan_id=group.plan_id,
            group_id=group.id,
            actor_type="member",
            actor_id=request.member_id,
            event_type="vote_added",
            event_data={"vote_type": request.vote_type, "comment": request.comment},
        )
        return vote

    def feedback_summary(self, group_id: str) -> GroupFeedbackSummarySchema:
        group = self._require_group(group_id)
        comments = self._comments_by_group[group.id]
        votes = self._votes_by_group[group.id]
        vote_counts = {"like": 0, "dislike": 0, "prefer": 0}
        for vote in votes:
            vote_counts[vote.vote_type] += 1
        constraints = self._infer_constraints(comments, votes)
        should_regenerate = bool(constraints) or vote_counts["dislike"] > vote_counts["like"]
        reason = (
            "Group feedback introduced new planning constraints."
            if should_regenerate
            else "Feedback is positive or insufficient for regeneration."
        )
        return GroupFeedbackSummarySchema(
            group_id=group.id,
            plan_id=group.plan_id,
            comment_count=len(comments),
            vote_count=len(votes),
            votes_by_type=vote_counts,
            new_constraints=constraints,
            should_regenerate_plan=should_regenerate,
            reason=reason,
            latest_comments=[comment.content for comment in comments[-5:]],
        )

    def _infer_constraints(self, comments: list[GroupCommentSchema], votes: list[PlanVoteSchema]) -> list[str]:
        text = " ".join([comment.content for comment in comments] + [vote.comment or "" for vote in votes]).lower()
        constraints: list[str] = []
        if any(token in text for token in ["oil", "greasy", "heavy", "light", "healthy", "qingdan"]):
            constraints.append("Prefer lighter and healthier dining")
        if any(token in text for token in ["far", "distance", "traffic", "too long"]):
            constraints.append("Reduce travel distance and route duration")
        if any(token in text for token in ["tired", "intense", "rest", "child"]):
            constraints.append("Lower activity intensity and keep rest time")
        if any(token in text for token in ["expensive", "budget", "price"]):
            constraints.append("Control per-person budget")
        if any(vote.vote_type == "dislike" for vote in votes):
            constraints.append("Avoid disliked plan elements")
        return list(dict.fromkeys(constraints))

    def _require_group(self, group_id: str) -> ActivityGroupSchema:
        group = self._groups.get(group_id)
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity group not found")
        return group

    def _require_share_link(self, token: str) -> ShareLinkSchema:
        share_link = self._share_links_by_token.get(token)
        if share_link is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
        if share_link.expires_at is not None and share_link.expires_at < _now():
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")
        return share_link

    def _require_member(self, group_id: str, member_id: str) -> GroupMemberSchema:
        for member in self._members_by_group.get(group_id, []):
            if member.id == member_id and member.status == "joined":
                return member
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group member not found")


timeline_service = TimelineService()
trip_map_service = TripMapService(timeline_service=timeline_service)
collaboration_service = CollaborationService(timeline_service=timeline_service)


def _now() -> datetime:
    return datetime.now(UTC)


def _distance_meters(start: LocationSchema, end: LocationSchema) -> int:
    radius_meters = 6_371_000
    start_lat = radians(start.lat)
    end_lat = radians(end.lat)
    delta_lat = radians(end.lat - start.lat)
    delta_lng = radians(end.lng - start.lng)
    value = sin(delta_lat / 2) ** 2 + cos(start_lat) * cos(end_lat) * sin(delta_lng / 2) ** 2
    return round(radius_meters * 2 * asin(sqrt(value)))
