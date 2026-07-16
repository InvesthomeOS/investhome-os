import type { ReactNode } from 'react';

export type StatusChipTone = 'default' | 'success' | 'warning' | 'danger' | 'info';

export interface StatusChipProps {
  children: ReactNode;
  tone?: StatusChipTone;
  className?: string;
}

const TONE_CLASS: Record<StatusChipTone, string> = {
  default: 'ih-status-chip',
  success: 'ih-status-chip ih-status-chip--success',
  warning: 'ih-status-chip ih-status-chip--warning',
  danger: 'ih-status-chip ih-status-chip--danger',
  info: 'ih-status-chip ih-status-chip--info',
};

export function StatusChip({ children, tone = 'default', className }: StatusChipProps) {
  return (
    <span className={[TONE_CLASS[tone], className].filter(Boolean).join(' ')}>{children}</span>
  );
}
