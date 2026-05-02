"use client";

import { Link as LinkIcon, Copy, Users, Clock } from "@phosphor-icons/react";
import type { ShareLinkSchema } from "@/types/collaboration";

interface ShareLinkBoxProps {
  shareLink: ShareLinkSchema;
}

export function ShareLinkBox({ shareLink }: ShareLinkBoxProps) {
  const handleCopyLink = () => {
    const shareUrl = `${window.location.origin}/share/${shareLink.token}`;
    navigator.clipboard.writeText(shareUrl);
    alert("分享链接已复制到剪贴板");
  };

  const shareUrl = `${window.location.origin}/share/${shareLink.token}`;

  const formatDate = (dateString?: string | null) => {
    if (!dateString) return "永不过期";
    const date = new Date(dateString);
    return date.toLocaleDateString("zh-CN", {
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="space-y-4">
      {/* Share URL */}
      <div className="p-4 bg-card-soft rounded-xl">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <LinkIcon className="size-4 text-clay-orange" />
            <span className="text-sm font-medium text-ink">分享链接</span>
          </div>
          <button
            onClick={handleCopyLink}
            className="flex items-center gap-1 px-3 py-1.5 bg-clay-orange text-white rounded-lg text-xs font-medium hover:bg-clay-orange-dark transition-colors"
          >
            <Copy className="size-3" />
            复制链接
          </button>
        </div>

        <div className="p-3 bg-white rounded-lg border border-line">
          <p className="text-xs text-muted break-all">{shareUrl}</p>
        </div>
      </div>

      {/* Share Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-card-soft rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <Users className="size-4 text-muted" />
            <span className="text-xs text-muted">使用次数</span>
          </div>
          <p className="text-lg font-bold text-ink">{shareLink.usage_count}</p>
          {shareLink.max_uses && (
            <p className="text-xs text-muted">/ {shareLink.max_uses} 次</p>
          )}
        </div>

        <div className="p-3 bg-card-soft rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="size-4 text-muted" />
            <span className="text-xs text-muted">过期时间</span>
          </div>
          <p className="text-xs text-ink">{formatDate(shareLink.expires_at)}</p>
        </div>
      </div>

      {/* How to Share */}
      <div className="p-4 bg-pine-green/10 rounded-xl">
        <p className="text-xs text-pine-green leading-relaxed">
          将此链接发送给同行人，他们可以加入协作，查看行程方案，并参与讨论和投票。
        </p>
      </div>
    </div>
  );
}