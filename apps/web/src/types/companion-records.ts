import type { PlanSchema } from "./planning";
import type {
  ActivityGroupSchema,
  GroupMemberSchema,
  ShareLinkSchema,
  GroupCommentSchema,
  PlanVoteSchema,
  TimelineEventSchema,
  GroupFeedbackSummarySchema,
} from "./collaboration";

export type CompanionRecordStatus =
  | "active"
  | "has_feedback"
  | "waiting_confirmation"
  | "completed"
  | "cancelled";

export type CompanionRecord = {
  group: ActivityGroupSchema;
  plan: PlanSchema;

  members: GroupMemberSchema[];
  comments_count: number;
  votes_count: number;
  pending_feedback_count: number;

  latest_comment?: GroupCommentSchema | null;
  latest_event?: TimelineEventSchema | null;

  share_link?: ShareLinkSchema | null;

  status: CompanionRecordStatus;

  created_at: string;
  updated_at: string;
};

export type CompanionRecordListResponse = {
  items: CompanionRecord[];
  total: number;
  stats: {
    active_count: number;
    feedback_count: number;
    waiting_confirmation_count: number;
  };
};

export type CompanionRecordDetail = {
  group: ActivityGroupSchema;
  plan: PlanSchema;
  members: GroupMemberSchema[];
  share_links: ShareLinkSchema[];
  comments: GroupCommentSchema[];
  votes: PlanVoteSchema[];
  timeline: TimelineEventSchema[];
  feedback_summary: GroupFeedbackSummarySchema;
};