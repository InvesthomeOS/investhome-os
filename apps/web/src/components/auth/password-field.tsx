'use client';

import { useId, useState } from 'react';

import { togglePasswordVisibility } from '@/lib/auth/password-reset-ux';

type PasswordFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete: 'current-password' | 'new-password';
  showLabel: string;
  hideLabel: string;
  minLength?: number;
  required?: boolean;
  testId?: string;
};

function EyeIcon({ off }: { off: boolean }) {
  if (off) {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18">
        <path
          d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 5.1A10.8 10.8 0 0112 5c5 0 9.3 3.1 11 7-1 2.2-2.6 4.1-4.6 5.4M6.1 6.1C4.2 7.4 2.7 9.1 1.9 12c1.7 3.9 6 7 10.1 7 1.3 0 2.6-.2 3.8-.7"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
        />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18">
      <path
        d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}

export function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  showLabel,
  hideLabel,
  minLength,
  required = true,
  testId,
}: PasswordFieldProps) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  return (
    <div className="auth-form__field">
      <label htmlFor={id}>{label}</label>
      <div className="auth-password">
        <input
          id={id}
          data-testid={testId}
          type={visible ? 'text' : 'password'}
          autoComplete={autoComplete}
          required={required}
          minLength={minLength}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <button
          type="button"
          className="auth-password__toggle"
          aria-label={visible ? hideLabel : showLabel}
          aria-pressed={visible}
          data-testid={testId ? `${testId}-toggle` : undefined}
          onClick={() => {
            setVisible((current) => togglePasswordVisibility({ value, visible: current }).visible);
          }}
        >
          <EyeIcon off={visible} />
        </button>
      </div>
    </div>
  );
}
