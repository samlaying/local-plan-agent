"use client";

import { Crown, User } from "@phosphor-icons/react";
import type { GroupMemberSchema } from "@/types/collaboration";

interface CompanionMemberRowProps {
  member: GroupMemberSchema;
}

export function CompanionMemberRow({ member }: CompanionMemberRowProps) {
  const getRoleColor = (role: string) => {
    switch (role) {
      case "creator":
        return "text-clay-orange bg-clay-orange/10";
      case "admin":
        return "text-pine-green bg-pine-green/10";
      default:
        return "text-muted bg-muted/10";
    }
  };

  const getRoleText = (role: string) => {
    switch (role) {
      case "creator":
        return "创建者";
      case "admin":
        return "管理员";
      default:
        return "成员";
    }
  };

  const formatDate = (dateString: string) => {
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

  return (
    <div className="flex items-center gap-3 p-3 bg-card-soft rounded-xl">
      {/* Avatar */}
      <div className="flex-shrink-0">
        {member.avatar ? (
          <img
            src={member.avatar}
            alt={member.nickname}
            className="w-10 h-10 rounded-full object-cover"
          />
        ) : (
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-clay-orange to-pine-green flex items-center justify-center text-white font-semibold">
            {member.nickname.charAt(0).toUpperCase()}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-ink truncate">{member.nickname}</span>
          {member.role === "creator" && <Crown className="size-3 text-clay-orange" />}
          {member.role === "admin" && <User className="size-3 text-pine-green" />}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted">
          <span className={`px-2 py-0.5 rounded-full ${getRoleColor(member.role)}`}>
            {getRoleText(member.role)}
          </span>
          <span>·</span>
          <span>{formatDate(member.last_active_at)}活跃</span>
        </div>
      </div>
    </div>
  );
}