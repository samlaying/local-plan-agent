'use client';

import React from 'react';
import { cn } from '@/lib/utils';

interface Comment {
  id: string;
  author: string;
  authorAvatar?: string;
  content: string;
  createdAt: string;
  likes?: number;
}

interface CommentListProps {
  comments: Comment[];
  title?: string;
  emptyMessage?: string;
}

export const CommentList: React.FC<CommentListProps> = ({
  comments,
  title = '同行小札',
  emptyMessage = '还没有人发表小札，来说点什么吧'
}) => {
  if (comments.length === 0) {
    return (
      <div className="card-paper p-6 text-center">
        <div className="text-muted mb-2">📝</div>
        <div className="text-sm text-muted">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className="card-paper p-6">
      <h3 className="text-sm font-bold text-ink mb-4 flex items-center gap-2">
        <span>{title}</span>
        <span className="text-muted">· {comments.length} 条反馈</span>
      </h3>

      <div className="space-y-4">
        {comments.map((comment) => (
          <div
            key={comment.id}
            className="flex gap-3 pb-4 border-b border-line last:border-0 last:pb-0"
          >
            {/* 头像 */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-clay-orange/10 flex items-center justify-center text-clay-orange text-sm font-medium">
              {comment.author.charAt(0)}
            </div>

            {/* 内容 */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-medium text-ink">{comment.author}</span>
                <span className="text-xs text-muted">
                  {new Date(comment.createdAt).toLocaleString()}
                </span>
              </div>
              <div className="text-sm text-ink leading-relaxed">
                {comment.content}
              </div>

              {/* 点赞 */}
              {comment.likes !== undefined && (
                <div className="flex items-center gap-1 mt-2 text-xs text-muted">
                  <button className="hover:text-clay-orange transition-colors">
                    👍 {comment.likes}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};