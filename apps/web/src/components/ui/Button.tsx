import React from 'react';
import { cn } from '../../lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  children: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading = false, disabled = false, children, className, ...props }, ref) => {
    const baseStyles = "font-semibold rounded-full transition-all duration-300 disabled:pointer-events-none";

    const variantStyles = {
      primary: "bg-gradient-to-br from-clay-orange to-clay-orange-dark text-white shadow-clay hover:shadow-clay-hover hover:-translate-y-0.5 active:scale-95",
      secondary: "bg-card-bg text-clay-orange border border-clay-orange hover:bg-clay-orange hover:text-white",
      ghost: "bg-transparent text-muted hover:text-ink"
    };

    const sizeStyles = {
      sm: "h-9 px-4 text-sm",
      md: "h-11 px-6 text-base",
      lg: "h-13 px-8 text-lg"
    };

    return (
      <button
        ref={ref}
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          (disabled || loading) && "opacity-45 cursor-not-allowed",
          className
        )}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <span className="flex items-center gap-2">
            <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            <span>加载中...</span>
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';