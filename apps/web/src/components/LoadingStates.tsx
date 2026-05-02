'use client';

import React from 'react';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  onBack?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = '出错了',
  message = '加载失败，请重试',
  onRetry,
  onBack,
  className
}) => {
  return (
    <div className={cn('text-center py-12', className)}>
      <div className="text-4xl mb-4">😅</div>
      <h3 className="text-lg font-bold text-ink mb-2">{title}</h3>
      <p className="text-muted mb-6 max-w-sm mx-auto">{message}</p>
      <div className="flex gap-3 justify-center">
        {onRetry && (
          <Button variant="primary" onClick={onRetry}>
            再试一次
          </Button>
        )}
        {onBack && (
          <Button variant="ghost" onClick={onBack}>
            回到输入
          </Button>
        )}
      </div>
    </div>
  );
};

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = '加载中...',
  className
}) => {
  return (
    <div className={cn('text-center py-12', className)}>
      <div className="inline-block mb-4">
        <div className="flex gap-1">
          <div className="w-2 h-2 rounded-full bg-clay-orange animate-pulse"></div>
          <div className="w-2 h-2 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '150ms' }}></div>
          <div className="w-2 h-2 rounded-full bg-clay-orange animate-pulse" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
      <p className="text-muted">{message}</p>
    </div>
  );
};

interface EmptyStateProps {
  title?: string;
  message?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = '暂无内容',
  message = '这里还没有任何内容',
  action,
  className
}) => {
  return (
    <div className={cn('text-center py-12', className)}>
      <div className="text-4xl mb-4">📭</div>
      <h3 className="text-lg font-bold text-ink mb-2">{title}</h3>
      <p className="text-muted mb-6 max-w-sm mx-auto">{message}</p>
      {action && (
        <Button variant="primary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </div>
  );
};