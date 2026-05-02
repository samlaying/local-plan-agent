import React from 'react';
import { cn } from '../../lib/utils';

export type StatusType = 'pending' | 'success' | 'warning' | 'danger' | 'processing';

export interface StatusBadgeProps {
  status: StatusType;
  children: React.ReactNode;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, children, className }) => {
  const statusStyles = {
    pending: 'bg-gray-100 text-gray-700 border-gray-200',
    success: 'bg-pine-green-soft text-pine-green border-pine-green',
    warning: 'bg-yellow-50 text-warning border-warning',
    danger: 'bg-red-50 text-danger border-danger',
    processing: 'bg-clay-orange/10 text-clay-orange border-clay-orange animate-pulse',
  };

  const statusLabels = {
    pending: '待处理',
    success: '成功',
    warning: '注意',
    danger: '失败',
    processing: '处理中',
  };

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border',
        statusStyles[status],
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {children || statusLabels[status]}
    </div>
  );
};