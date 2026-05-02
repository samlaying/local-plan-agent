import React from 'react';
import { cn } from '../../lib/utils';

export interface LoadingDotsProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingDots: React.FC<LoadingDotsProps> = ({ className, size = 'md' }) => {
  const sizeStyles = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5'
  };

  return (
    <div className={cn('flex items-center gap-1', className)}>
      <div className={cn('rounded-full bg-clay-orange animate-pulse', sizeStyles[size])} style={{ animationDelay: '0ms' }} />
      <div className={cn('rounded-full bg-clay-orange animate-pulse', sizeStyles[size])} style={{ animationDelay: '150ms' }} />
      <div className={cn('rounded-full bg-clay-orange animate-pulse', sizeStyles[size])} style={{ animationDelay: '300ms' }} />
    </div>
  );
};