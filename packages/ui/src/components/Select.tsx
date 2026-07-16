import type { ReactNode, SelectHTMLAttributes } from 'react';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: ReactNode;
}

export function Select({ label, id, className, children, ...props }: SelectProps) {
  const selectId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  return (
    <label className="ih-field" htmlFor={selectId}>
      {label ? <span className="ih-field__label">{label}</span> : null}
      <select id={selectId} className={`ih-select${className ? ` ${className}` : ''}`} {...props}>
        {children}
      </select>
    </label>
  );
}
