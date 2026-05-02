"use client";

import { Users, Link as LinkIcon, ChatCircle, CheckCircle, Clock, Copy } from "@phosphor-icons/react";
import type { CompanionRecordDetail as CompanionRecordDetailType } from "@/types/companion-records";
import { CompanionMemberRow } from "@/components/companions/CompanionMemberRow";
import { CompanionTimeline } from "@/components/companions/CompanionTimeline";
import { UnresolvedFeedbackPanel } from "@/components/companions/UnresolvedFeedbackPanel";
import { ShareLinkBox } from "@/components/companions/ShareLinkBox";

interface CompanionRecordDetailProps {
  record: CompanionRecordDetailType;
}

export function CompanionRecordDetail({ record }: CompanionRecordDetailProps) {
  const shareLink = record.share_links[0] ?? null;
  const pendingFeedbackCount = record.feedback_summary.should_regenerate_plan
    ? record.feedback_summary.new_constraints.length || record.comments.length
    : 0;

  const handleCopyShareLink = () => {
    if (shareLink) {
      const shareUrl = `${window.location.origin}/share/${shareLink.token}`;
      navigator.clipboard.writeText(shareUrl);
      alert("分享链接已复制到剪贴板");
    }
  };

  return (
    <div className="space-y-6">
      {/* Plan Overview */}
      <div className="bg-card-bg rounded-xl p-6 shadow-paper">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-ink mb-2">{record.plan.title}</h2>
            <p className="text-sm text-muted">{record.plan.summary}</p>
          </div>

          {/* Share Link */}
          {shareLink && (
            <button
              onClick={handleCopyShareLink}
              className="flex items-center gap-2 px-4 py-2 bg-clay-orange text-white rounded-lg hover:bg-clay-orange-dark transition-colors text-sm font-medium"
            >
              <LinkIcon className="size-4" />
              复制分享链接
              <Copy className="size-4" />
            </button>
          )}
        </div>

        {/* Plan Stats */}
        <div className="grid grid-cols-3 gap-4 p-4 bg-card-soft rounded-xl">
          <div className="text-center">
            <div className="text-2xl font-bold text-ink">{record.plan.totalDurationMinutes / 60}</div>
            <div className="text-xs text-muted">小时</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-ink">{record.plan.pois.length}</div>
            <div className="text-xs text-muted">地点</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-ink">{record.plan.score.toFixed(1)}</div>
            <div className="text-xs text-muted">评分</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Members */}
        <div className="bg-card-bg rounded-xl p-6 shadow-paper">
          <div className="flex items-center gap-2 mb-4">
            <Users className="size-5 text-clay-orange" />
            <h3 className="text-lg font-semibold text-ink">同行人</h3>
          </div>

          <div className="space-y-3">
            {record.members.map((member) => (
              <CompanionMemberRow key={member.id} member={member} />
            ))}
          </div>
        </div>

        {/* Collaboration Stats */}
        <div className="bg-card-bg rounded-xl p-6 shadow-paper">
          <div className="flex items-center gap-2 mb-4">
            <ChatCircle className="size-5 text-pine-green" />
            <h3 className="text-lg font-semibold text-ink">协作状态</h3>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-card-soft rounded-xl">
              <div className="flex items-center gap-2">
                <ChatCircle className="size-4 text-muted" />
                <span className="text-sm text-ink">评论</span>
              </div>
              <span className="text-lg font-bold text-ink">{record.comments.length}</span>
            </div>

            <div className="flex items-center justify-between p-3 bg-card-soft rounded-xl">
              <div className="flex items-center gap-2">
                <CheckCircle className="size-4 text-muted" />
                <span className="text-sm text-ink">投票</span>
              </div>
              <span className="text-lg font-bold text-ink">{record.votes.length}</span>
            </div>

            {pendingFeedbackCount > 0 && (
              <div className="flex items-center justify-between p-3 bg-warning/10 rounded-xl">
                <div className="flex items-center gap-2">
                  <Clock className="size-4 text-warning" />
                  <span className="text-sm text-ink">待处理反馈</span>
                </div>
                <span className="text-lg font-bold text-warning">{pendingFeedbackCount}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="bg-card-bg rounded-xl p-6 shadow-paper">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="size-5 text-clay-orange" />
          <h3 className="text-lg font-semibold text-ink">同行时间线</h3>
        </div>

        <CompanionTimeline events={record.timeline} />
      </div>

      {/* Unresolved Feedback */}
      {pendingFeedbackCount > 0 && (
        <div className="bg-card-bg rounded-xl p-6 shadow-paper">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle className="size-5 text-warning" />
            <h3 className="text-lg font-semibold text-ink">未处理反馈</h3>
          </div>

          <UnresolvedFeedbackPanel feedbackSummary={record.feedback_summary} />
        </div>
      )}

      {/* Share Links */}
      {shareLink && (
        <div className="bg-card-bg rounded-xl p-6 shadow-paper">
          <div className="flex items-center gap-2 mb-4">
            <LinkIcon className="size-5 text-pine-green" />
            <h3 className="text-lg font-semibold text-ink">分享链接</h3>
          </div>

          <ShareLinkBox shareLink={shareLink} />
        </div>
      )}
    </div>
  );
}
