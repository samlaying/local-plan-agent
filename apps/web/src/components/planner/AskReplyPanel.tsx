'use client';

import React, { useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { Button } from '@/components/ui';

export const AskReplyPanel: React.FC = () => {
  const { userIntent, askQuestion, sendUserReply } = useWorkbench();
  const [replyText, setReplyText] = useState('');

  const handleSend = () => {
    const trimmed = replyText.trim();
    if (!trimmed) return;
    sendUserReply(trimmed);
    setReplyText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* 用户原始需求 */}
      <div className="card-paper p-6 mb-6">
        <div className="text-xs text-muted mb-1">你的需求</div>
        <p className="text-ink">{userIntent || '…'}</p>
      </div>

      {/* 追问卡片 */}
      <div className="card-paper p-6 border-2 border-clay-orange">
        <h2 className="text-lg font-bold text-ink mb-1">Agent 需要补充一些信息</h2>
        <p className="text-muted text-sm mb-4">回答后会继续为你生成路线</p>

        {askQuestion && (
          <p className="text-ink font-medium mb-4">{askQuestion.question}</p>
        )}

        <div className="flex gap-3">
          <textarea
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的回答…（Enter 发送，Shift+Enter 换行）"
            rows={3}
            className="flex-1 bg-card-bg border border-line rounded-xl px-4 py-3 text-sm text-ink placeholder:text-muted resize-none focus:outline-none focus:border-clay-orange"
          />
          <Button
            onClick={handleSend}
            disabled={!replyText.trim()}
            className="self-end"
            size="md"
          >
            发送
          </Button>
        </div>
      </div>
    </div>
  );
};
