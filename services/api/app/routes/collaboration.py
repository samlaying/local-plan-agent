from fastapi import APIRouter, Query

from services.api.app.schemas.collaboration import (
    AddCommentRequest,
    AddVoteRequest,
    CreateGroupRequest,
    CreateShareLinkRequest,
    CreateTripMapRequest,
    GroupCommentSchema,
    GroupFeedbackSummarySchema,
    GroupMemberSchema,
    GroupSnapshotSchema,
    JoinShareRequest,
    MapStopSchema,
    PlanVoteSchema,
    ShareLinkSchema,
    SharePageSnapshotSchema,
    TimelineEventSchema,
    TripMapSnapshotSchema,
    UpdateMapStopStatusRequest,
)
from services.api.app.services.collaboration import collaboration_service, timeline_service, trip_map_service

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


@router.post("/maps", response_model=TripMapSnapshotSchema)
def create_trip_map(request: CreateTripMapRequest) -> TripMapSnapshotSchema:
    return trip_map_service.create_from_plan(request)


@router.get("/maps/{trip_map_id}", response_model=TripMapSnapshotSchema)
def get_trip_map(trip_map_id: str) -> TripMapSnapshotSchema:
    return trip_map_service.get_snapshot(trip_map_id)


@router.patch("/maps/stops/{stop_id}/status", response_model=MapStopSchema)
def update_map_stop_status(stop_id: str, request: UpdateMapStopStatusRequest) -> MapStopSchema:
    return trip_map_service.update_stop_status(stop_id, request)


@router.post("/groups", response_model=GroupSnapshotSchema)
def create_group(request: CreateGroupRequest) -> GroupSnapshotSchema:
    return collaboration_service.create_group(request)


@router.post("/groups/{group_id}/share-links", response_model=ShareLinkSchema)
def create_share_link(group_id: str, request: CreateShareLinkRequest) -> ShareLinkSchema:
    return collaboration_service.create_share_link(group_id, request)


@router.get("/shares/{token}", response_model=SharePageSnapshotSchema)
def get_share_page(token: str) -> SharePageSnapshotSchema:
    return collaboration_service.get_share_page(token)


@router.post("/shares/{token}/join", response_model=GroupMemberSchema)
def join_share(token: str, request: JoinShareRequest) -> GroupMemberSchema:
    return collaboration_service.join_share(token, request.guest_name)


@router.post("/groups/{group_id}/comments", response_model=GroupCommentSchema)
def add_comment(group_id: str, request: AddCommentRequest) -> GroupCommentSchema:
    return collaboration_service.add_comment(group_id, request)


@router.post("/groups/{group_id}/votes", response_model=PlanVoteSchema)
def add_vote(group_id: str, request: AddVoteRequest) -> PlanVoteSchema:
    return collaboration_service.add_vote(group_id, request)


@router.get("/groups/{group_id}/feedback-summary", response_model=GroupFeedbackSummarySchema)
def get_feedback_summary(group_id: str) -> GroupFeedbackSummarySchema:
    return collaboration_service.feedback_summary(group_id)


@router.get("/timeline", response_model=list[TimelineEventSchema])
def list_timeline(
    plan_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
) -> list[TimelineEventSchema]:
    return timeline_service.list_events(plan_id=plan_id, group_id=group_id)
