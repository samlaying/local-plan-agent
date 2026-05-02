import type { PlanSchema } from "./planning";

export type TravelJournalStatus =
  | "draft"
  | "planned"
  | "ongoing"
  | "completed"
  | "archived";

export type TravelJournalScene =
  | "family"
  | "friends"
  | "couple"
  | "solo"
  | "team";

export type TravelJournal = {
  id: string;
  user_id: string;

  title: string;
  subtitle?: string | null;
  cover_image_url?: string | null;

  source_plan_id?: string | null;
  source_trip_map_id?: string | null;
  source_group_id?: string | null;

  status: TravelJournalStatus;
  scene: TravelJournalScene;

  city: string;
  district?: string | null;

  started_at?: string | null;
  ended_at?: string | null;

  total_duration_minutes?: number | null;
  total_distance_meters?: number | null;
  stop_count: number;
  photo_count: number;

  tags: string[];

  is_favorite: boolean;
  is_public: boolean;

  summary?: string | null;
  agent_review?: string | null;

  created_at: string;
  updated_at: string;
};

export type JournalStop = {
  id: string;
  journal_id: string;

  source_stop_id?: string | null;
  poi_id?: string | null;

  name: string;
  type: "origin" | "activity" | "meal" | "rest" | "destination";

  address?: string | null;
  lat?: number | null;
  lng?: number | null;

  planned_arrival_time?: string | null;
  planned_leave_time?: string | null;

  actual_arrival_time?: string | null;
  actual_leave_time?: string | null;

  estimated_stay_minutes?: number | null;
  actual_stay_minutes?: number | null;

  status: "planned" | "visited" | "skipped";

  agent_reason?: string | null;
  user_note?: string | null;

  created_at: string;
};

export type JournalPhoto = {
  id: string;
  journal_id: string;
  stop_id?: string | null;

  url: string;
  thumbnail_url?: string | null;

  caption?: string | null;
  taken_at?: string | null;

  source: "mock" | "upload" | "generated" | "external";

  created_at: string;
};

export type TravelJournalDetail = {
  journal: TravelJournal;
  plan?: PlanSchema | null;
  trip_map?: any | null;
  stops: JournalStop[];
  photos: JournalPhoto[];
  timeline: any[];
  companions: any[];
};

export type JournalListResponse = {
  items: TravelJournal[];
  total: number;
  page: number;
  page_size: number;
};

export type CreateJournalFromTripMapRequest = {
  trip_map_id: string;
  user_id?: string;
  title?: string;
  save_photos?: boolean;
};

export type UpdateJournalRequest = {
  title?: string;
  summary?: string;
  tags?: string[];
  is_favorite?: boolean;
  is_public?: boolean;
};