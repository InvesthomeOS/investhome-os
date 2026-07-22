import type { HTMLAttributes, ReactNode } from 'react';

export interface DashboardRowProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

export function DashboardRow({ children, className, ...props }: DashboardRowProps) {
  return (
    <div className={`ds-dashboard-row${className ? ` ${className}` : ''}`} {...props}>
      {children}
    </div>
  );
}
