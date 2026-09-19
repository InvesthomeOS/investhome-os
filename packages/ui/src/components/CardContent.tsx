import type { ReactNode } from 'react';

export interface CardContentProps {
  children?: ReactNode;
  className?: string;
}

export function CardContent({ children, className }: CardContentProps) {
  return <div className={`ds-card__content${className ? ` ${className}` : ''}`}>{children}</div>;
}
