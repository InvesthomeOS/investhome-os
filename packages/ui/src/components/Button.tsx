import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary' | 'ghost' | 'danger' | 'link';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  children: ReactNode;
  /** Shows spinner and disables interaction */
  loading?: boolean;
  /** Brief success affordance (green fill) */
  success?: boolean;
}

const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: 'ih-btn ih-btn--primary',
  secondary: 'ih-btn ih-btn--secondary',
  tertiary: 'ih-btn ih-btn--tertiary',
  ghost: 'ih-btn ih-btn--ghost',
  danger: 'ih-btn ih-btn--danger',
  link: 'ih-btn ih-btn--link',
};

export function Button({
  variant = 'primary',
  size = 'md',
  className,
  children,
  loading = false,
  success = false,
  disabled,
  ...props
}: ButtonProps) {
  const classes = [
    VARIANT_CLASS[variant],
    size !== 'md' ? `ih-btn--${size}` : '',
    loading ? 'ih-btn--loading' : '',
    success && !loading ? 'ih-btn--success' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      type="button"
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {children}
    </button>
  );
}
