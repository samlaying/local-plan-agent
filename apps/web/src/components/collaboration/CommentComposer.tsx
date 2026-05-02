'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface CommentComposerProps {
  onSubmit?: (content: string) => Promise<void>;
  placeholder?: string;
  minLength?: number;
  maxLength?: number;
}

export const CommentComposer: React.FC<CommentComposerProps> = ({
  onSubmit,
  placeholder = '写一句同行小札...',
  minLength = 2,
  maxLength = 200
}) => {
  const [content, setContent] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (content.trim().length < minLength) {
      return;
    }

    try {
      setSubmitting(true);
      if (onSubmit) {
        await onSubmit(content);
      }
      setContent('');
    } catch (error) {
      console.error('Failed to submit comment:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const charCount = content.length;
  const canSubmit = charCount >= minLength && charCount <= maxLength && !submitting;

  return (
    <div className="card-paper p-4">
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder={placeholder}
        maxLength={maxLength}
        className={cn(
          'w-full min-h-[80px] bg-transparent text-ink placeholder:text-muted resize-none focus:outline-none',
          submitting && 'opacity-60 pointer-events-none'
        )}
        disabled={submitting}
      />

      {/* 底部工具栏 */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-line">
        <div className="text-xs text-muted">
          {charCount}/{maxLength}
        </div>

        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={!canSubmit}
          loading={submitting}
        >
          发送
        </Button>
      </div>

      {/* 字数提示 */}
      {charCount > 0 && charCount < minLength && (
        <div className="mt-2 text-xs text-muted">
          再写 {minLength - charCount} 个字就可以发送了
        </div>
      )}
    </div>
  );
};