import type { ReactNode } from 'react';

export type StatusBadgeTone = 'success' | 'warning' | 'danger' | 'info' | 'ai' | 'neutral';

export interface StatusBadgeProps {
  tone?: StatusBadgeTone;
  children: ReactNode;
  className?: string;
}

export function StatusBadge({ tone = 'neutral', children, className }: StatusBadgeProps) {
  return (
    <span className={`ds-status-badge ds-status-badge--${tone}${className ? ` ${className}` : ''}`}>
      {children}
    </span>
  );
}
