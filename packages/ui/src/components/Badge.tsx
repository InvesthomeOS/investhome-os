import type { ReactNode } from 'react';

export type BadgeTone = 'default' | 'success' | 'warning' | 'danger' | 'info';

export interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}

const TONE_CLASS: Record<BadgeTone, string> = {
  default: 'dashboard-shell__nav-badge',
  success: 'ih-badge ih-badge--success',
  warning: 'ih-badge ih-badge--warning',
  danger: 'ih-badge ih-badge--danger',
  info: 'ih-badge ih-badge--info',
};

export function Badge({ children, tone = 'default', className }: BadgeProps) {
  return <span className={[TONE_CLASS[tone], className].filter(Boolean).join(' ')}>{children}</span>;
}
