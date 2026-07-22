import type { HTMLAttributes, ReactNode } from 'react';

export interface DashboardGridProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

/** 12-col desktop / 8-col tablet / 1-col mobile via CSS. Gap 24px desktop / 16px mobile. */
export function DashboardGrid({ children, className, ...props }: DashboardGridProps) {
  return (
    <div className={`ds-dashboard-grid${className ? ` ${className}` : ''}`} {...props}>
      {children}
    </div>
  );
}
