export type TripMapSnapshotSchema = {
  id: string;
  trip_map_id: string;
  plan_id: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  stops: TripMapStopSchema[];
  route_segments: RouteSegmentSchema[];
  total_distance_meters: number;
  estimated_duration_minutes: number;
  metadata: Record<string, unknown>;
};

export type TripMapStopSchema = {
  id: string;
  trip_map_id: string;
  sequence_order: number;
  poi_id: string;
  type: "origin" | "activity" | "meal" | "rest" | "destination";
  status: "pending" | "in_progress" | "completed";
  planned_arrival_time: string;
  planned_departure_time: string;
  notes: string;
  created_at: string;
};

export type RouteSegmentSchema = {
  id: string;
  trip_map_id: string;
  from_stop_id: string;
  to_stop_id: string;
  travel_mode: "driving" | "taxi" | "public_transit" | "walking";
  distance_meters: number;
  estimated_duration_minutes: number;
  route_geometry: string;
};

export type GroupMemberSchema = {
  id: string;
  group_id: string;
  nickname: string;
  avatar?: string | null;
  role: "creator" | "admin" | "member";
  joined_at: string;
  last_active_at: string;
};

export type ActivityGroupSchema = {
  id: string;
  trip_map_id: string;
  name: string;
  description?: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type ShareLinkSchema = {
  id: string;
  group_id: string;
  token: string;
  created_by: string;
  expires_at?: string | null;
  max_uses?: number | null;
  usage_count: number;
  created_at: string;
};

export type GroupCommentSchema = {
  id: string;
  group_id: string;
  member_id: string;
  content: string;
  created_at: string;
  updated_at: string;
};

export type PlanVoteSchema = {
  id: string;
  group_id: string;
  member_id: string;
  plan_preference: "plan_a" | "plan_b" | "plan_c";
  created_at: string;
};

export type TimelineEventSchema = {
  id: string;
  plan_id: string;
  event_type: "created" | "updated" | "commented" | "voted" | "status_changed";
  actor_id: string;
  actor_nickname: string;
  description: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type GroupFeedbackSummarySchema = {
  group_id: string;
  plan_id: string;
  comment_count: number;
  vote_count: number;
  votes_by_type: Record<string, number>;
  new_constraints: string[];
  should_regenerate_plan: boolean;
  reason: string;
  latest_comments: string[];
};
