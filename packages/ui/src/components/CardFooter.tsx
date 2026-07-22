import type { ReactNode } from 'react';

export interface CardFooterProps {
  children?: ReactNode;
  className?: string;
}

export function CardFooter({ children, className }: CardFooterProps) {
  return <div className={`ds-card__footer${className ? ` ${className}` : ''}`}>{children}</div>;
}
