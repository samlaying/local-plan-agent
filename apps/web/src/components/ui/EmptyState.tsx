import React from 'react';
import { CheckCircleIcon } from '../icons';
import { cn } from '../../lib/utils';

export interface EmptyStateProps {
  title: string;
  description: string;
  className?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, description, className, action }) => {
  return (
    <div className={cn('flex flex-col items-center justify-center py-12 px-6 text-center', className)}>
      <div className="w-16 h-16 rounded-full bg-pine-green-soft flex items-center justify-center mb-6">
        <CheckCircleIcon className="w-8 h-8 text-pine-green" />
      </div>
      <h3 className="text-xl font-bold text-ink mb-2">{title}</h3>
      <p className="text-muted mb-6 max-w-md">{description}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="btn-primary"
        >
          {action.label}
        </button>
      )}
    </div>
  );
};