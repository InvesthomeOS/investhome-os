import type { ReactNode } from 'react';

export interface RightRailCardProps {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}

export function RightRailCard({ title, children, action, className }: RightRailCardProps) {
  return (
    <aside className={`ds-right-rail-card${className ? ` ${className}` : ''}`}>
      <div className="ds-widget-shell__header" style={{ padding: 0 }}>
        <h3 className="ds-right-rail-card__title">{title}</h3>
        {action}
      </div>
      <div className="ds-right-rail-card__body">{children}</div>
    </aside>
  );
}
