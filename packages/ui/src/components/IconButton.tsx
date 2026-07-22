import type { ButtonHTMLAttributes, ReactNode } from 'react';

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  children: ReactNode;
  variant?: 'default' | 'ghost';
}

export function IconButton({
  label,
  children,
  variant = 'default',
  className,
  type = 'button',
  ...props
}: IconButtonProps) {
  const classes = [
    'ds-icon-button',
    variant === 'ghost' ? 'ds-icon-button--ghost' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button type={type} className={classes} aria-label={label} title={label} {...props}>
      {children}
    </button>
  );
}
