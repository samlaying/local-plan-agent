export type InspirationType =
  | "poi"
  | "route"
  | "quote"
  | "photo"
  | "article"
  | "restaurant"
  | "activity"
  | "map"
  | "note";

export type InspirationSource =
  | "plan"
  | "journal"
  | "city_guide"
  | "manual"
  | "external"
  | "companion_feedback";

export type InspirationItem = {
  id: string;
  user_id: string;

  type: InspirationType;

  title: string;
  description?: string | null;

  cover_image_url?: string | null;

  source: InspirationSource;
  source_id?: string | null;

  city: string;
  district?: string | null;

  location?: {
    lat: number;
    lng: number;
    address?: string | null;
  } | null;

  tags: string[];

  content?: string | null;

  payload: Record<string, unknown>;

  group_id?: string | null;

  is_archived: boolean;

  created_at: string;
  updated_at: string;
};

export type InspirationCollection = {
  id: string;
  user_id: string;

  name: string;
  description?: string | null;

  cover_image_url?: string | null;

  item_count: number;

  created_at: string;
  updated_at: string;
};

export type InspirationListResponse = {
  items: InspirationItem[];
  total: number;
  stats?: {
    total: number;
    collections: number;
    visited_places: number;
  };
};

export type InspirationCollectionListResponse = {
  items: InspirationCollection[];
  total: number;
};

export type CreateInspirationRequest = {
  type: InspirationType;
  title: string;
  description?: string;
  city: string;
  district?: string;
  tags?: string[];
  source: InspirationSource;
  source_id?: string;
  content?: string;
  payload?: Record<string, unknown>;
};

export type CreateCollectionRequest = {
  name: string;
  description?: string;
};