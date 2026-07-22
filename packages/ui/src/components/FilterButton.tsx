import type { ButtonHTMLAttributes, ReactNode } from 'react';

export interface FilterButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  active?: boolean;
  count?: number;
}

export function FilterButton({
  children,
  active = false,
  count,
  className,
  type = 'button',
  ...props
}: FilterButtonProps) {
  const classes = [
    'ds-filter-button',
    active ? 'ds-filter-button--active' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button type={type} className={classes} aria-pressed={active} {...props}>
      {children}
      {typeof count === 'number' ? <span className="ds-filter-button__count">{count}</span> : null}
    </button>
  );
}
