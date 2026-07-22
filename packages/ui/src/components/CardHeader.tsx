import type { ReactNode } from 'react';

export interface CardHeaderProps {
  title?: string;
  description?: string;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
}

export function CardHeader({ title, description, action, children, className }: CardHeaderProps) {
  return (
    <div className={`ds-card__header${className ? ` ${className}` : ''}`}>
      <div className="ds-card__header-text">
        {title ? <h3 className="ds-card__title">{title}</h3> : null}
        {description ? <p className="ds-card__description">{description}</p> : null}
        {children}
      </div>
      {action}
    </div>
  );
}
