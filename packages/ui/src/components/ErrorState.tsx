import type { ReactNode } from 'react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  action?: ReactNode;
  className?: string;
  compact?: boolean;
}

export function ErrorState({
  title,
  message,
  action,
  className,
  compact = false,
}: ErrorStateProps) {
  return (
    <div
      className={`ih-error${compact ? ' ih-error--compact' : ''}${className ? ` ${className}` : ''}`}
      role="alert"
    >
      {title ? <h3 className="ih-error__title">{title}</h3> : null}
      <p className="ih-error__message">{message}</p>
      {action ? <div className="ih-error__action">{action}</div> : null}
    </div>
  );
}
