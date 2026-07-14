import type { ReactNode } from 'react';

export interface CardProps {
  title: string;
  description?: string;
  children?: ReactNode;
}

export function Card({ title, description, children }: CardProps) {
  return (
    <article className="ih-card">
      <h3 className="ih-card__title">{title}</h3>
      {description ? <p className="ih-card__description">{description}</p> : null}
      {children}
    </article>
  );
}
