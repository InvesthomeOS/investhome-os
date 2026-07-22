import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  error?: ReactNode;
  hint?: ReactNode;
  success?: boolean;
}

export function Input({ label, id, className, error, hint, success, ...props }: InputProps) {
  const inputId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  const fieldClass = [
    'ih-field',
    'auth-form__field',
    error ? 'ih-field--error' : null,
    success && !error ? 'ih-field--success' : null,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <label className={fieldClass} htmlFor={inputId}>
      {label ? <span className="ih-field__label">{label}</span> : null}
      <input
        id={inputId}
        className={`ih-input${className ? ` ${className}` : ''}`}
        aria-invalid={error ? true : undefined}
        data-state={success && !error ? 'success' : undefined}
        {...props}
      />
      {error ? (
        <span className="ih-field__error" role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className="ih-field__hint">{hint}</span>
      ) : null}
    </label>
  );
}

export interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: ReactNode;
  error?: ReactNode;
  hint?: ReactNode;
  success?: boolean;
}

export function TextArea({ label, id, className, error, hint, success, ...props }: TextAreaProps) {
  const inputId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  const fieldClass = [
    'ih-field',
    'auth-form__field',
    error ? 'ih-field--error' : null,
    success && !error ? 'ih-field--success' : null,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <label className={fieldClass} htmlFor={inputId}>
      {label ? <span className="ih-field__label">{label}</span> : null}
      <textarea
        id={inputId}
        className={`ih-input ih-input--textarea${className ? ` ${className}` : ''}`}
        aria-invalid={error ? true : undefined}
        data-state={success && !error ? 'success' : undefined}
        {...props}
      />
      {error ? (
        <span className="ih-field__error" role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className="ih-field__hint">{hint}</span>
      ) : null}
    </label>
  );
}
