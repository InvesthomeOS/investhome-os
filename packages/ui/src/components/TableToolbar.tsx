import type { ReactNode } from 'react';

export interface TableToolbarProps {
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function TableToolbar({ children, actions, className }: TableToolbarProps) {
  return (
    <div className={`ih-table-toolbar${className ? ` ${className}` : ''}`}>
      <div className="ih-table-toolbar__filters">{children}</div>
      {actions ? <div className="ih-table-toolbar__actions">{actions}</div> : null}
    </div>
  );
}
