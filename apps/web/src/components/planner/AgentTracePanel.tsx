'use client';

import React, { useRef, useEffect, useState } from 'react';
import { useWorkbench } from '@/features/planner/contexts/WorkbenchContext';
import { CheckCircleIcon, ClockIcon } from '../icons';
import { cn } from '@/lib/utils';

export const AgentTracePanel: React.FC = () => {
  const {
    userIntent,
    traceEvents,
    askQuestion,
    sendUserReply,
  } = useWorkbench();

  const [replyText, setReplyText] = useState('');
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll trace list when new events arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [traceEvents]);

  const handleSendReply = () => {
    const trimmed = replyText.trim();
    if (!trimmed) return;
    sendUserReply(trimmed);
    setReplyText('');
  };

  const handleReplyKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendReply();
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* 用户输入摘要 */}
      <div className="card-paper p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-ink">你的需求</h3>
        </div>
        <p className="text-ink mb-4">{userIntent || '今天下午想和老婆孩子出去玩几个小时，别离家太远'}</p>
      </div>

      {/* Agent 处理追踪 */}
      <div className="card-paper p-6 mb-6">
        <h3 className="text-lg font-bold text-ink mb-2">Agent 理解中</h3>
        <p className="text-muted mb-4">正在理解你的偏好，马上为你生成路线</p>

        {/* Trace 事件列表 */}
        <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
          {traceEvents.length === 0 && (
            <div className="flex items-center gap-2 text-sm text-muted">
              <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" />
              <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '300ms' }} />
              <span>等待 Agent 响应…</span>
            </div>
          )}

          {traceEvents.map((event, index) => {
            const isLast = index === traceEvents.length - 1;
            const isRunning = event.status === 'running';
            const isDone = event.status === 'done';
            const isFailed = event.status === 'error';

            const Icon = isDone ? CheckCircleIcon : ClockIcon;

            return (
              <div
                key={index}
                className={cn(
                  'card-paper p-4 transition-all duration-200',
                  isRunning && 'border-clay-orange shadow-clay',
                  isDone && 'border-pine-green',
                  isFailed && 'border-danger'
                )}
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon
                    className={cn(
                      'w-4 h-4 flex-shrink-0',
                      isRunning && 'text-clay-orange animate-pulse',
                      isDone && 'text-pine-green',
                      isFailed && 'text-danger',
                      !isRunning && !isDone && !isFailed && 'text-muted'
                    )}
                  />
                  <span className="text-sm font-medium text-ink">{event.agent}</span>
                </div>
                <p className="text-xs text-muted pl-6">{event.message}</p>

                {isRunning && isLast && (
                  <div className="flex items-center gap-1 pl-6 mt-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" />
                    <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            );
          })}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* Agent 追问 */}
      {askQuestion && (
        <div className="card-paper p-6 mb-6 border-clay-orange">
          <h3 className="text-lg font-bold text-ink mb-2">Agent 需要更多信息</h3>
          <p className="text-ink mb-4">{askQuestion.question}</p>

          <div className="flex gap-3">
            <textarea
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              onKeyDown={handleReplyKeyDown}
              placeholder="输入你的回答…（Enter 发送）"
              rows={2}
              className="flex-1 bg-card-bg border border-line rounded-xl px-4 py-3 text-sm text-ink placeholder:text-muted resize-none focus:outline-none focus:border-clay-orange"
            />
            <button
              onClick={handleSendReply}
              disabled={!replyText.trim()}
              className="px-5 py-2 rounded-xl bg-clay-orange text-white text-sm font-medium disabled:opacity-40 hover:bg-clay-orange/90 transition-colors self-end"
            >
              发送
            </button>
          </div>
        </div>
      )}

      {/* Skeleton 加载状态 */}
      <div className="space-y-4">
        {/* 路线地图预览 */}
        <div className="card-paper p-6">
          <h4 className="text-sm font-bold text-ink mb-3">路线地图预览（生成中）</h4>
          <div className="skeleton h-48 rounded-xl bg-card-soft" />
        </div>

        {/* 行程时间预览 */}
        <div className="card-paper p-6">
          <h4 className="text-sm font-bold text-ink mb-3">行程时间预览（生成中）</h4>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-12 rounded-lg bg-card-soft" />
            ))}
          </div>
        </div>

        {/* 路线方案预览 */}
        <div className="card-paper p-6">
          <h4 className="text-sm font-bold text-ink mb-3">路线方案预览（生成中）</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-32 rounded-xl bg-card-soft" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
