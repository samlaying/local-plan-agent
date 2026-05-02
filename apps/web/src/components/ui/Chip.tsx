import React from 'react';
import { cn } from '../../lib/utils';

export interface ChipProps {
  children: React.ReactNode;
  className?: string;
  selected?: boolean;
  onClick?: () => void;
}

export const Chip = React.forwardRef<HTMLDivElement, ChipProps>(
  ({ children, className, selected = false, onClick }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'chip',
          selected && 'selected',
          onClick && 'cursor-pointer',
          className
        )}
        onClick={onClick}
      >
        {children}
      </div>
    );
  }
);

Chip.displayName = 'Chip';