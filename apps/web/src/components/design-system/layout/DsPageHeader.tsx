import type { ReactNode } from 'react';

export interface DsPageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  className?: string;
}

/** Layout page header using Design System v1.0 tokens (does not replace @investhome/ui PageHeader). */
export function DsPageHeader({ eyebrow, title, subtitle, actions, className }: DsPageHeaderProps) {
  return (
    <header className={`ds-page-header${className ? ` ${className}` : ''}`}>
      <div className="ds-page-header__text">
        {eyebrow ? <p className="ds-page-header__eyebrow">{eyebrow}</p> : null}
        <h1 className="ds-page-header__title">{title}</h1>
        {subtitle ? <p className="ds-page-header__subtitle">{subtitle}</p> : null}
      </div>
      {actions ? <div className="ds-page-header__actions">{actions}</div> : null}
    </header>
  );
}
