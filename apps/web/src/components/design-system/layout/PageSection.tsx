import type { ReactNode } from 'react';

export interface PageSectionProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  id?: string;
}

export function PageSection({ title, description, actions, children, className, id }: PageSectionProps) {
  return (
    <section id={id} className={`ds-page-section${className ? ` ${className}` : ''}`}>
      {(title || actions) && (
        <div className="ds-page-section__header">
          <div>
            {title ? <h2 className="ds-type-section-title">{title}</h2> : null}
            {description ? <p className="ds-type-body-small">{description}</p> : null}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
