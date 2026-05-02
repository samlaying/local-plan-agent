export type CityArticleCategory =
  | "weekly_feature"
  | "neighborhood_walk"
  | "cafe_bookstore"
  | "museum_exhibition"
  | "family_day"
  | "rainy_day"
  | "city_calendar";

export type CityArticle = {
  id: string;

  city: string;
  district?: string | null;

  title: string;
  subtitle?: string | null;
  excerpt: string;
  content: string;

  cover_image_url?: string | null;

  category: CityArticleCategory;

  tags: string[];

  reading_minutes: number;

  editor_name?: string | null;

  related_poi_ids: string[];
  related_route_ids: string[];

  is_featured: boolean;
  is_published: boolean;

  published_at: string;
  updated_at: string;
};

export type CityTopic = {
  id: string;

  city: string;
  title: string;
  description: string;

  cover_image_url?: string | null;

  article_ids: string[];
  route_ids: string[];

  tags: string[];

  created_at: string;
  updated_at: string;
};

export type CityRoute = {
  id: string;

  city: string;
  district?: string | null;

  title: string;
  description: string;

  cover_image_url?: string | null;

  duration_minutes: number;
  distance_km: number;

  route_type:
    | "city_walk"
    | "family"
    | "cafe"
    | "museum"
    | "rainy_day"
    | "weekend";

  stops: CityRouteStop[];

  tags: string[];

  created_at: string;
  updated_at: string;
};

export type CityRouteStop = {
  id: string;
  route_id: string;

  name: string;
  type: "activity" | "meal" | "rest" | "viewpoint";

  address?: string | null;
  lat?: number | null;
  lng?: number | null;

  order_index: number;

  description?: string | null;
  recommended_stay_minutes?: number | null;
};

export type CityEvent = {
  id: string;

  city: string;
  district?: string | null;

  title: string;
  description?: string | null;

  location_name?: string | null;
  address?: string | null;

  starts_at: string;
  ends_at?: string | null;

  category: "music" | "exhibition" | "market" | "family" | "walk" | "other";

  price_info?: string | null;
  booking_url?: string | null;

  tags: string[];

  created_at: string;
};

export type CityGuideHomeResponse = {
  featured_article?: CityArticle | null;
  weekly_topic?: CityTopic | null;
  articles: CityArticle[];
  routes: CityRoute[];
  events: CityEvent[];
  editor_picks: CityArticle[];
};

export type CityArticleListResponse = {
  items: CityArticle[];
  total: number;
  page: number;
  page_size: number;
};

export type CityRouteListResponse = {
  items: CityRoute[];
  total: number;
  page: number;
  page_size: number;
};

export type CityEventListResponse = {
  items: CityEvent[];
  total: number;
};