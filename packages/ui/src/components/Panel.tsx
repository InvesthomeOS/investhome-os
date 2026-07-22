import type { ReactNode } from 'react';

export interface PanelProps {
  title?: string;
  description?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  bodyClassName?: string;
  id?: string;
}

export function Panel({
  title,
  description,
  badge,
  actions,
  children,
  className,
  bodyClassName,
  id,
}: PanelProps) {
  return (
    <section id={id} className={`ih-panel${className ? ` ${className}` : ''}`}>
      {(title || actions || badge) && (
        <header className="ih-panel__header">
          <div className="ih-panel__heading">
            {title ? <h2 className="ih-panel__title">{title}</h2> : null}
            {badge ? <span className="ih-panel__badge">{badge}</span> : null}
            {description ? <p className="ih-panel__description">{description}</p> : null}
          </div>
          {actions ? <div className="ih-panel__actions">{actions}</div> : null}
        </header>
      )}
      <div className={`ih-panel__body${bodyClassName ? ` ${bodyClassName}` : ''}`}>{children}</div>
    </section>
  );
}
