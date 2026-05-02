CREATE TABLE IF NOT EXISTS user_profiles (
  session_id TEXT PRIMARY KEY,
  preference_weights JSONB NOT NULL DEFAULT '{}',
  selected_poi_ids JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
