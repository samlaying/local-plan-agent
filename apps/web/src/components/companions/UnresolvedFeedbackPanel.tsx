"use client";

import { Warning, ChatCircle, CheckCircle } from "@phosphor-icons/react";
import type { GroupFeedbackSummarySchema } from "@/types/collaboration";

interface UnresolvedFeedbackPanelProps {
  feedbackSummary: GroupFeedbackSummarySchema | null;
}

export function UnresolvedFeedbackPanel({ feedbackSummary }: UnresolvedFeedbackPanelProps) {
  if (!feedbackSummary || feedbackSummary.new_constraints.length === 0) {
    return (
      <div className="text-center py-6 text-muted">
        <CheckCircle className="size-8 text-success/30 mx-auto mb-2" />
        <p>所有反馈都已处理完毕</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {feedbackSummary.new_constraints.map((issue, index) => (
        <div
          key={index}
          className="p-4 bg-warning/10 border border-warning/20 rounded-xl"
        >
          <div className="flex items-start gap-3">
            <Warning className="size-5 text-warning flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-ink mb-2">{issue}</p>
              <div className="flex items-center gap-2">
                <button className="px-3 py-1.5 bg-warning text-white rounded-lg text-xs font-medium hover:bg-warning-dark transition-colors">
                  处理反馈
                </button>
                <button className="px-3 py-1.5 bg-white border border-line text-muted rounded-lg text-xs font-medium hover:bg-card-soft transition-colors">
                  暂时忽略
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
