import type { ReactNode } from 'react';

export interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
  /** Compact density for widgets — does not break existing callers */
  compact?: boolean;
}

export function EmptyState({
  title,
  description,
  action,
  icon,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={`ih-empty${compact ? ' ih-empty--compact' : ''}${className ? ` ${className}` : ''}`}
    >
      {icon ? <div className="ih-empty__icon">{icon}</div> : null}
      <h3 className="ih-empty__title">{title}</h3>
      {description ? <p className="ih-empty__description">{description}</p> : null}
      {action ? <div className="ih-empty__action">{action}</div> : null}
    </div>
  );
}
