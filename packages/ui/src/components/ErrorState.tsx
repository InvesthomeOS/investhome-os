import type { ReactNode } from 'react';

export interface ErrorStateProps {
  title?: string;
  message: string;
  action?: ReactNode;
}

export function ErrorState({ title = 'Something went wrong', message, action }: ErrorStateProps) {
  return (
    <div className="admin-detail">
      <h2>{title}</h2>
      <p className="auth-form__error">{message}</p>
      {action}
    </div>
  );
}
