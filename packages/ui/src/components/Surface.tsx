import type { HTMLAttributes, ReactNode } from 'react';

export type SurfaceVariant = 'default' | 'subtle' | 'elevated' | 'flush';

export interface SurfaceProps extends HTMLAttributes<HTMLDivElement> {
  variant?: SurfaceVariant;
  children?: ReactNode;
  as?: 'div' | 'section' | 'article';
}

export function Surface({
  variant = 'default',
  children,
  className,
  as: Comp = 'div',
  ...props
}: SurfaceProps) {
  const classes = [
    'ds-surface',
    variant !== 'default' ? `ds-surface--${variant}` : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <Comp className={classes} {...props}>
      {children}
    </Comp>
  );
}
