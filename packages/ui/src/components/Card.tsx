import type { ReactNode } from 'react';

export interface CardProps {
  /** Legacy simple card title — when set with no compound children pattern, renders classic layout */
  title?: string;
  description?: string;
  children?: ReactNode;
  className?: string;
}

/**
 * Card surface. Backward compatible: `<Card title="…">` still works.
 * Prefer compound: `<Card><CardHeader /><CardContent /><CardFooter /></Card>`.
 */
export function Card({ title, description, children, className }: CardProps) {
  const hasLegacyTitle = Boolean(title);

  if (hasLegacyTitle) {
    return (
      <article className={`ih-card ds-card${className ? ` ${className}` : ''}`}>
        <h3 className="ih-card__title ds-card__title">{title}</h3>
        {description ? <p className="ih-card__description ds-card__description">{description}</p> : null}
        {children}
      </article>
    );
  }

  return <article className={`ds-card${className ? ` ${className}` : ''}`}>{children}</article>;
}
