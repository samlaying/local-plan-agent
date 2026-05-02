"use client";

import { CheckCircle, ChatCircle, CheckSquare, Clock } from "@phosphor-icons/react";
import type { TimelineEventSchema } from "@/types/collaboration";

interface CompanionTimelineProps {
  events: TimelineEventSchema[];
}

export function CompanionTimeline({ events }: CompanionTimelineProps) {
  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case "created":
        return CheckCircle;
      case "updated":
        return CheckSquare;
      case "commented":
        return ChatCircle;
      case "voted":
        return CheckCircle;
      case "status_changed":
        return Clock;
      default:
        return Clock;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case "created":
        return "text-success bg-success/10";
      case "updated":
        return "text-pine-green bg-pine-green/10";
      case "commented":
        return "text-clay-orange bg-clay-orange/10";
      case "voted":
        return "text-pine-green bg-pine-green/10";
      case "status_changed":
        return "text-warning bg-warning/10";
      default:
        return "text-muted bg-muted/10";
    }
  };

  const getEventText = (eventType: string) => {
    switch (eventType) {
      case "created":
        return "创建了行程";
      case "updated":
        return "更新了行程";
      case "commented":
        return "发表了评论";
      case "voted":
        return "参与了投票";
      case "status_changed":
        return "更改了状态";
      default:
        return "进行了操作";
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString("zh-CN");
  };

  if (events.length === 0) {
    return (
      <div className="text-center py-8 text-muted">
        <Clock className="size-8 text-muted/30 mx-auto mb-2" />
        <p>还没有时间线记录</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {events.map((event, index) => {
        const EventIcon = getEventIcon(event.event_type);
        return (
          <div key={event.id} className="flex items-start gap-3">
            {/* Icon */}
            <div className={`p-2 rounded-full ${getEventColor(event.event_type)} flex-shrink-0`}>
              <EventIcon className="size-4" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pb-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-ink">{event.actor_nickname}</span>
                <span className="text-sm text-muted">{getEventText(event.event_type)}</span>
              </div>
              {event.description && (
                <p className="text-xs text-muted mb-1">{event.description}</p>
              )}
              <span className="text-xs text-muted/60">{formatTime(event.created_at)}</span>
            </div>

            {/* Connector Line */}
            {index < events.length - 1 && (
              <div className="absolute left-4 mt-12 w-0.5 h-8 bg-line" />
            )}
          </div>
        );
      })}
    </div>
  );
}