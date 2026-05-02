"use client";

import { Calendar, Users, ChatCircle, CheckCircle } from "@phosphor-icons/react";
import type { CompanionRecord } from "@/types/companion-records";

interface CompanionRecordListProps {
  records: CompanionRecord[];
  selectedRecordId: string | null;
  onSelectRecord: (recordId: string) => void;
  getStatusColor: (status: string) => string;
  getStatusText: (status: string) => string;
  getStatusIcon: (status: string) => any;
}

export function CompanionRecordList({
  records,
  selectedRecordId,
  onSelectRecord,
  getStatusColor,
  getStatusText,
  getStatusIcon,
}: CompanionRecordListProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-CN", {
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="space-y-3">
      {records.map((record) => {
        const StatusIcon = getStatusIcon(record.status);
        return (
          <button
            key={record.group.id}
            onClick={() => onSelectRecord(record.group.id)}
            className={`w-full text-left bg-card-bg rounded-xl p-4 shadow-paper hover:shadow-paper-hover transition-all duration-300 ${
              selectedRecordId === record.group.id
                ? "ring-2 ring-clay-orange"
                : ""
            }`}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-semibold text-ink line-clamp-1 mb-1">
                  {record.plan.title}
                </h3>
                <div className="flex items-center gap-2 text-xs text-muted">
                  <Calendar className="size-3" />
                  <span>{formatDate(record.created_at)}</span>
                </div>
              </div>

              {/* Status Badge */}
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 flex-shrink-0 ${getStatusColor(
                  record.status
                )}`}
              >
                <StatusIcon className="size-3" />
                {getStatusText(record.status)}
              </span>
            </div>

            {/* Summary */}
            {record.plan.summary && (
              <p className="text-sm text-muted mb-3 line-clamp-2">
                {record.plan.summary}
              </p>
            )}

            {/* Stats */}
            <div className="flex items-center gap-3 text-xs text-muted">
              <div className="flex items-center gap-1">
                <Users className="size-3" />
                <span>{record.members.length}人</span>
              </div>
              <div className="flex items-center gap-1">
                <ChatCircle className="size-3" />
                <span>{record.comments_count}</span>
              </div>
              <div className="flex items-center gap-1">
                <CheckCircle className="size-3" />
                <span>{record.votes_count}</span>
              </div>
              {record.pending_feedback_count > 0 && (
                <div className="ml-auto text-warning">
                  {record.pending_feedback_count} 条待处理
                </div>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}