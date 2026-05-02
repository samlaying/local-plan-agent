'use client';

import React from 'react';
import { UsersIcon } from '../icons';
import { cn } from '@/lib/utils';

interface Member {
  id: string;
  name: string;
  avatar?: string;
  status: 'joined' | 'pending';
  joinedAt?: string;
}

interface MemberListProps {
  members: Member[];
  totalSlots?: number;
}

export const MemberList: React.FC<MemberListProps> = ({
  members,
  totalSlots = 6
}) => {
  return (
    <div className="card-paper p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-ink flex items-center gap-2">
          <UsersIcon className="w-4 h-4" />
          已加入的同行 {members.length}/{totalSlots}
        </h3>
        <button className="text-xs text-clay-orange hover:underline">
          邀请更多
        </button>
      </div>

      {/* 成员头像列表 */}
      <div className="flex flex-wrap gap-2 mb-4">
        {members.map((member) => (
          <div
            key={member.id}
            className="relative group"
          >
            <div
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center text-white font-medium text-sm',
                member.status === 'joined' ? 'bg-clay-orange' : 'bg-muted'
              )}
            >
              {member.name.charAt(0)}
            </div>
            {/* 状态指示 */}
                <div
                  className={cn(
                    'absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white',
                    member.status === 'joined' ? 'bg-pine-green' : 'bg-gray-300'
                  )}
                ></div>
            </div>
          ))}

        {/* 添加成员按钮 */}
        {members.length < totalSlots && (
          <button className="w-10 h-10 rounded-full bg-card-soft border-2 border-dashed border-line flex items-center justify-center text-muted hover:border-clay-orange hover:text-clay-orange transition-colors">
            <span className="text-lg">+</span>
          </button>
        )}
      </div>

      {/* 成员列表 */}
      <div className="space-y-2">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between text-sm"
          >
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-clay-orange/10 flex items-center justify-center text-clay-orange text-xs">
                {member.name.charAt(0)}
              </div>
              <span className="text-ink">{member.name}</span>
            </div>
            <div className="flex items-center gap-2">
              {member.status === 'joined' ? (
                <>
                  <span className="text-pine-green text-xs">已加入</span>
                  {member.joinedAt && (
                    <span className="text-muted text-xs">
                      {new Date(member.joinedAt).toLocaleTimeString()}
                    </span>
                  )}
                </>
              ) : (
                <span className="text-muted text-xs">等待中</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};