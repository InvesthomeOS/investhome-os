import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  children: ReactNode;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: 'leads__button leads__button--primary',
  secondary: 'leads__button leads__button--secondary',
  ghost: 'leads__button leads__button--ghost',
  danger: 'leads__button leads__button--danger',
};

export function Button({ variant = 'primary', className, children, ...props }: ButtonProps) {
  const classes = [VARIANT_CLASS[variant], className].filter(Boolean).join(' ');
  return (
    <button type="button" className={classes} {...props}>
      {children}
    </button>
  );
}
