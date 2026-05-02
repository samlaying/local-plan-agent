export type ParticipantType = "adult" | "child" | "elder";

export type TravelMode = "driving" | "taxi" | "public_transit" | "walking";

export type POICategory =
  | "family_activity"
  | "friends_activity"
  | "restaurant";

export type PriceLevel = "low" | "medium" | "high";

export type ActionType =
  | "navigation"
  | "reservation"
  | "queue"
  | "ticket"
  | "order"
  | "message"
  | "calendar";

export type ActionStatus =
  | "pending"
  | "needs_confirmation"
  | "mocked"
  | "success"
  | "failed";

export interface Participant {
  type: ParticipantType;
  count: number;
  age?: number;
  relationship?: string;
  notes?: string[];
}

export interface TimeWindow {
  date: string;
  start?: string;
  end?: string;
  label?: string;
}

export interface UserIntent {
  rawText: string;
  city: string;
  origin: string;
  timeWindow: TimeWindow;
  durationHours: {
    min: number;
    max: number;
  };
  participants: Participant[];
  travelMode: TravelMode;
  maxDistanceKm: number;
  budgetPerPerson?: number;
  hardConstraints: string[];
  softPreferences: string[];
  dietRequirements: string[];
  scenario: "family_weight_loss_child5" | "friends_4_mixed_gender";
}

export interface BusinessHours {
  open: string;
  close: string;
  lastEntry?: string;
  note?: string;
}

export interface AudienceFit {
  family: number;
  childAge5: number;
  weightLossFriendly: number;
  friendsGroup: number;
  mixedGenderGroup: number;
}

export interface QueueInfo {
  waitMinutes: number;
  level: "none" | "low" | "medium" | "high";
  note?: string;
}

export interface POI {
  id: string;
  provider: "mock" | "amap";
  name: string;
  category: POICategory;
  subcategory: string;
  address: string;
  city: string;
  distanceKm: number;
  travelMinutes: number;
  pricePerPerson: number;
  priceLevel: PriceLevel;
  rating: number;
  audienceFit: AudienceFit;
  businessHours: BusinessHours;
  reservable: boolean;
  queue: QueueInfo;
  recommendedDurationMinutes: number;
  tags: string[];
  suitableScenarios: UserIntent["scenario"][];
  reasons: string[];
  cautions: string[];
  location: {
    lat: number;
    lng: number;
  };
}

export interface ItineraryStep {
  id: string;
  type: "activity" | "meal" | "extra" | "transit";
  title: string;
  poiId?: string;
  startTime: string;
  endTime: string;
  durationMinutes: number;
  description: string;
  fitReasons: string[];
  risks: string[];
  actionRefs: string[];
}

export interface ExecutableAction {
  id: string;
  planId: string;
  type: ActionType;
  title: string;
  provider: "mock" | "amap" | "system";
  status: ActionStatus;
  requiresUserConfirmation: boolean;
  payload: Record<string, unknown>;
  result?: Record<string, unknown>;
}

export interface ItineraryPlan {
  id: string;
  title: string;
  summary: string;
  scenario: UserIntent["scenario"];
  totalDurationMinutes: number;
  estimatedCost: {
    min: number;
    max: number;
    currency: "CNY";
  };
  score: number;
  riskLevel: "low" | "medium" | "high";
  steps: ItineraryStep[];
  pois: POI[];
  actions: ExecutableAction[];
  fitSummary: string[];
  tradeoffs: string[];
}
