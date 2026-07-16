import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: 'ih-btn ih-btn--primary',
  secondary: 'ih-btn ih-btn--secondary',
  ghost: 'ih-btn ih-btn--ghost',
  danger: 'ih-btn ih-btn--danger',
};

export function Button({ variant = 'primary', className, children, ...props }: ButtonProps) {
  const classes = [VARIANT_CLASS[variant], className].filter(Boolean).join(' ');
  return (
    <button type="button" className={classes} {...props}>
      {children}
    </button>
  );
}
