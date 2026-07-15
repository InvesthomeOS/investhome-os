import type { ReactNode } from 'react';

export interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ eyebrow, title, subtitle, actions }: PageHeaderProps) {
  return (
    <header className="dashboard__header">
      <div>
        {eyebrow ? <p className="dashboard__eyebrow">{eyebrow}</p> : null}
        <h1 className="dashboard__title">{title}</h1>
        {subtitle ? <p className="dashboard__subtitle">{subtitle}</p> : null}
      </div>
      {actions}
    </header>
  );
}
