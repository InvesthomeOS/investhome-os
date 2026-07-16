import type { ReactNode } from 'react';

export interface TableProps {
  children: ReactNode;
  className?: string;
  wrapClassName?: string;
}

export function Table({ children, className = 'ih-table admin-table', wrapClassName = 'ih-table-wrap admin-table-wrap' }: TableProps) {
  return (
    <div className={wrapClassName}>
      <table className={className}>{children}</table>
    </div>
  );
}
