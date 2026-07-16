import type { InputHTMLAttributes, ReactNode } from 'react';

export interface SearchInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: ReactNode;
}

export function SearchInput({ label, id, className, ...props }: SearchInputProps) {
  const inputId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  return (
    <label className="ih-field" htmlFor={inputId}>
      {label ? <span className="ih-field__label">{label}</span> : null}
      <input
        id={inputId}
        type="search"
        className={`ih-search-input${className ? ` ${className}` : ''}`}
        {...props}
      />
    </label>
  );
}
