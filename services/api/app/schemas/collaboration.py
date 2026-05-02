from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from services.api.app.schemas.planning import LocationSchema, PlanSchema


RouteMode = Literal["driving", "walking", "transit", "taxi"]
TripMapStatus = Literal["planned", "active", "completed", "cancelled"]
MapProviderName = Literal["mock", "amap", "google"]
MapStopType = Literal["origin", "activity", "meal", "rest", "destination"]
MapStopStatus = Literal["pending", "going", "arrived", "completed", "skipped"]
TrafficStatus = Literal["smooth", "slow", "congested", "unknown"]
GroupScene = Literal["family", "friends", "couple", "team"]
GroupStatus = Literal["active", "confirmed", "completed", "cancelled"]
MemberRole = Literal["owner", "member", "guest"]
MemberStatus = Literal["invited", "joined", "left"]
SharePermission = Literal["view", "comment", "vote", "collaborate"]
CommentTargetType = Literal["plan", "stop", "restaurant", "activity"]
VoteType = Literal["like", "dislike", "prefer"]
TimelineActorType = Literal["user", "agent", "member", "system"]
TimelineEventType = Literal[
    "request_created",
    "intent_parsed",
    "plans_generated",
    "plan_shared",
    "member_joined",
    "comment_added",
    "vote_added",
    "plan_updated",
    "plan_confirmed",
    "action_executed",
    "map_updated",
    "trip_completed",
]


class TripMapSchema(BaseModel):
    id: str
    plan_id: str
    user_id: str
    start_location: LocationSchema
    end_location: LocationSchema | None = None
    route_mode: RouteMode
    total_distance_meters: int = Field(ge=0)
    total_duration_minutes: int = Field(ge=0)
    status: TripMapStatus
    map_provider: MapProviderName
    created_at: datetime
    updated_at: datetime


class MapStopSchema(BaseModel):
    id: str
    trip_map_id: str
    plan_id: str
    poi_id: str | None = None
    name: str
    type: MapStopType
    location: LocationSchema
    order_index: int = Field(ge=0)
    planned_arrival_time: str
    planned_leave_time: str
    estimated_stay_minutes: int = Field(ge=0)
    status: MapStopStatus
    notes: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RouteSegmentSchema(BaseModel):
    id: str
    trip_map_id: str
    from_stop_id: str
    to_stop_id: str
    distance_meters: int = Field(ge=0)
    duration_minutes: int = Field(ge=0)
    polyline: str
    route_mode: RouteMode
    traffic_status: TrafficStatus = "unknown"
    provider_raw: dict[str, Any] | None = None
    created_at: datetime


class TripMapSnapshotSchema(BaseModel):
    trip_map: TripMapSchema
    stops: list[MapStopSchema]
    route_segments: list[RouteSegmentSchema]


class CreateTripMapRequest(BaseModel):
    plan: PlanSchema
    user_id: str = "user_demo"
    start_location: LocationSchema
    end_location: LocationSchema | None = None
    route_mode: RouteMode = "driving"


class UpdateMapStopStatusRequest(BaseModel):
    status: MapStopStatus


class ActivityGroupSchema(BaseModel):
    id: str
    owner_id: str
    plan_id: str
    name: str
    scene: GroupScene
    status: GroupStatus
    share_code: str
    created_at: datetime
    updated_at: datetime


class GroupMemberSchema(BaseModel):
    id: str
    group_id: str
    user_id: str | None = None
    guest_name: str | None = None
    guest_avatar_seed: str | None = None
    role: MemberRole
    status: MemberStatus
    last_seen_at: datetime
    created_at: datetime


class ShareLinkSchema(BaseModel):
    id: str
    group_id: str
    plan_id: str
    token: str
    permission: SharePermission
    expires_at: datetime | None = None
    open_count: int = Field(ge=0)
    created_at: datetime


class GroupCommentSchema(BaseModel):
    id: str
    group_id: str
    plan_id: str
    member_id: str
    content: str
    target_type: CommentTargetType | None = None
    target_id: str | None = None
    created_at: datetime


class PlanVoteSchema(BaseModel):
    id: str
    group_id: str
    plan_id: str
    member_id: str
    vote_type: VoteType
    comment: str | None = None
    created_at: datetime


class TimelineEventSchema(BaseModel):
    id: str
    plan_id: str
    group_id: str | None = None
    actor_type: TimelineActorType
    actor_id: str | None = None
    event_type: TimelineEventType
    event_data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class GroupSnapshotSchema(BaseModel):
    group: ActivityGroupSchema
    owner_member: GroupMemberSchema
    share_link: ShareLinkSchema | None = None


class CreateGroupRequest(BaseModel):
    plan: PlanSchema
    owner_id: str = "user_demo"
    name: str
    scene: GroupScene = "family"
    share_permission: SharePermission = "comment"


class CreateShareLinkRequest(BaseModel):
    permission: SharePermission = "comment"
    expires_at: datetime | None = None


class JoinShareRequest(BaseModel):
    guest_name: str = Field(min_length=1)


class SharePageSnapshotSchema(BaseModel):
    group: ActivityGroupSchema
    share_link: ShareLinkSchema
    plan: PlanSchema
    members: list[GroupMemberSchema]
    comments: list[GroupCommentSchema]
    votes: list[PlanVoteSchema]
    timeline: list[TimelineEventSchema]


class AddCommentRequest(BaseModel):
    member_id: str
    content: str = Field(min_length=1)
    target_type: CommentTargetType | None = None
    target_id: str | None = None


class AddVoteRequest(BaseModel):
    member_id: str
    vote_type: VoteType
    comment: str | None = None


class GroupFeedbackSummarySchema(BaseModel):
    group_id: str
    plan_id: str
    comment_count: int
    vote_count: int
    votes_by_type: dict[str, int]
    new_constraints: list[str]
    should_regenerate_plan: bool
    reason: str
    latest_comments: list[str]
