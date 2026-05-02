CREATE TABLE IF NOT EXISTS trip_maps (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  start_location_json JSONB NOT NULL,
  end_location_json JSONB,
  route_mode TEXT NOT NULL,
  total_distance_meters INTEGER NOT NULL DEFAULT 0,
  total_duration_minutes INTEGER NOT NULL DEFAULT 0,
  map_provider TEXT NOT NULL DEFAULT 'mock',
  status TEXT NOT NULL DEFAULT 'planned',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS map_stops (
  id TEXT PRIMARY KEY,
  trip_map_id TEXT NOT NULL REFERENCES trip_maps(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL,
  poi_id TEXT,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  location_json JSONB NOT NULL,
  order_index INTEGER NOT NULL,
  planned_arrival_time TEXT NOT NULL,
  planned_leave_time TEXT NOT NULL,
  estimated_stay_minutes INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending',
  notes JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS route_segments (
  id TEXT PRIMARY KEY,
  trip_map_id TEXT NOT NULL REFERENCES trip_maps(id) ON DELETE CASCADE,
  from_stop_id TEXT NOT NULL REFERENCES map_stops(id) ON DELETE CASCADE,
  to_stop_id TEXT NOT NULL REFERENCES map_stops(id) ON DELETE CASCADE,
  distance_meters INTEGER NOT NULL DEFAULT 0,
  duration_minutes INTEGER NOT NULL DEFAULT 0,
  polyline TEXT NOT NULL,
  route_mode TEXT NOT NULL,
  traffic_status TEXT NOT NULL DEFAULT 'unknown',
  provider_raw JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activity_groups (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  plan_id TEXT NOT NULL,
  name TEXT NOT NULL,
  scene TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',
  share_code TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS group_members (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES activity_groups(id) ON DELETE CASCADE,
  user_id TEXT,
  guest_name TEXT,
  guest_avatar_seed TEXT,
  role TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'joined',
  last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS share_links (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES activity_groups(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL,
  token TEXT NOT NULL UNIQUE,
  permission TEXT NOT NULL,
  expires_at TIMESTAMPTZ,
  open_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS group_comments (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES activity_groups(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL,
  member_id TEXT NOT NULL REFERENCES group_members(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  target_type TEXT,
  target_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plan_votes (
  id TEXT PRIMARY KEY,
  group_id TEXT NOT NULL REFERENCES activity_groups(id) ON DELETE CASCADE,
  plan_id TEXT NOT NULL,
  member_id TEXT NOT NULL REFERENCES group_members(id) ON DELETE CASCADE,
  vote_type TEXT NOT NULL,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS timeline_events (
  id TEXT PRIMARY KEY,
  plan_id TEXT NOT NULL,
  group_id TEXT,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  event_type TEXT NOT NULL,
  event_data_json JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trip_maps_plan_id ON trip_maps(plan_id);
CREATE INDEX IF NOT EXISTS idx_map_stops_trip_map_id ON map_stops(trip_map_id);
CREATE INDEX IF NOT EXISTS idx_activity_groups_plan_id ON activity_groups(plan_id);
CREATE INDEX IF NOT EXISTS idx_group_members_group_id ON group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_share_links_token ON share_links(token);
CREATE INDEX IF NOT EXISTS idx_group_comments_group_id ON group_comments(group_id);
CREATE INDEX IF NOT EXISTS idx_plan_votes_group_id ON plan_votes(group_id);
CREATE INDEX IF NOT EXISTS idx_timeline_events_plan_group ON timeline_events(plan_id, group_id);
