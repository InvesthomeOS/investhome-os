import type { ReactNode } from 'react';

export type AlertTone = 'info' | 'success' | 'warning' | 'error';

export interface AlertProps {
  children: ReactNode;
  tone?: AlertTone;
  role?: 'status' | 'alert';
  className?: string;
}

const TONE_CLASS: Record<AlertTone, string> = {
  info: 'ih-alert ih-alert--info',
  success: 'ih-alert ih-alert--success',
  warning: 'ih-alert ih-alert--warning',
  error: 'ih-alert ih-alert--error',
};

export function Alert({ children, tone = 'info', role = 'status', className }: AlertProps) {
  return (
    <div className={[TONE_CLASS[tone], className].filter(Boolean).join(' ')} role={role}>
      {children}
    </div>
  );
}
