import type { ReactNode } from 'react';

export interface FilterBarProps {
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function FilterBar({ children, actions, className }: FilterBarProps) {
  return (
    <div className={`ih-filter-bar${className ? ` ${className}` : ''}`}>
      <div className="ih-filter-bar__fields">{children}</div>
      {actions ? <div className="ih-filter-bar__actions">{actions}</div> : null}
    </div>
  );
}
