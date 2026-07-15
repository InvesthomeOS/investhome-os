import type { InputHTMLAttributes, ReactNode } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
}

export function Input({ label, id, className, ...props }: InputProps) {
  const inputId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  return (
    <label className="auth-form__field" htmlFor={inputId}>
      {label ? <span>{label}</span> : null}
      <input id={inputId} className={className} {...props} />
    </label>
  );
}

export interface TextAreaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: ReactNode;
}

export function TextArea({ label, id, className, ...props }: TextAreaProps) {
  const inputId = id ?? (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  return (
    <label className="auth-form__field" htmlFor={inputId}>
      {label ? <span>{label}</span> : null}
      <textarea id={inputId} className={className} {...props} />
    </label>
  );
}
