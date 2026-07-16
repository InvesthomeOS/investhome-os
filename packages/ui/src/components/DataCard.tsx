import type { ReactNode } from 'react';

export interface DataCardProps {
  title: string;
  children: ReactNode;
  className?: string;
  footer?: ReactNode;
}

export function DataCard({ title, children, className, footer }: DataCardProps) {
  return (
    <article className={`ih-data-card${className ? ` ${className}` : ''}`}>
      <header className="ih-data-card__header">
        <h3 className="ih-data-card__title">{title}</h3>
      </header>
      <div className="ih-data-card__body">{children}</div>
      {footer ? <footer className="ih-data-card__footer">{footer}</footer> : null}
    </article>
  );
}
