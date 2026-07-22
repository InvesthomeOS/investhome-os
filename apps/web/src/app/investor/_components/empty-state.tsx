import type { ReactNode } from 'react';

export interface EmptyStateProps {
  icon?: string;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  children?: ReactNode;
}

export function EmptyState({
  icon = '◇',
  title,
  description,
  actionLabel,
  onAction,
  children,
}: EmptyStateProps) {
  return (
    <div className="inv-empty-state">
      <span className="inv-empty-state__icon" aria-hidden="true">
        {icon}
      </span>
      <h3 className="inv-empty-state__title">{title}</h3>
      <p className="inv-empty-state__description">{description}</p>
      {actionLabel && onAction ? (
        <button type="button" className="inv-empty-state__action" onClick={onAction}>
          {actionLabel}
        </button>
      ) : null}
      {children}
    </div>
  );
}
