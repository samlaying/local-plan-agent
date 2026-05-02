CREATE TABLE IF NOT EXISTS planning_requests (
  id UUID PRIMARY KEY,
  raw_text TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS itinerary_plans (
  id UUID PRIMARY KEY,
  request_id UUID NOT NULL REFERENCES planning_requests(id),
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  score NUMERIC,
  status TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS execution_actions (
  id UUID PRIMARY KEY,
  plan_id UUID NOT NULL REFERENCES itinerary_plans(id),
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  status TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}',
  result JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
