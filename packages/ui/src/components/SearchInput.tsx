'use client';

import type { InputHTMLAttributes, ReactNode } from 'react';

export interface SearchInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: ReactNode;
  loading?: boolean;
  onClear?: () => void;
  clearLabel?: string;
}

export function SearchInput({
  label,
  id,
  className,
  loading = false,
  onClear,
  clearLabel = 'Clear',
  value,
  ...props
}: SearchInputProps) {
  const inputId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  const hasValue = typeof value === 'string' ? value.length > 0 : value != null;
  const showClear = Boolean(onClear && hasValue && !loading);

  return (
    <label className="ih-field" htmlFor={inputId}>
      {label ? <span className="ih-field__label">{label}</span> : null}
      <span className="ih-search">
        <input
          id={inputId}
          type="search"
          className={`ih-search-input ih-search__input${className ? ` ${className}` : ''}`}
          value={value}
          {...props}
        />
        {loading ? <span className="ih-search__spinner" aria-hidden="true" /> : null}
        {showClear ? (
          <button type="button" className="ih-search__clear" onClick={onClear} aria-label={clearLabel}>
            ×
          </button>
        ) : null}
      </span>
    </label>
  );
}
