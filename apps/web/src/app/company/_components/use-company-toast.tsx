'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

import { ApiError } from '@/lib/api/client';

export type CompanyToastTone = 'success' | 'warning' | 'error' | 'permission';

export type CompanyToast = {
  id: string;
  tone: CompanyToastTone;
  message: string;
};

type CompanyToastContextValue = {
  toasts: CompanyToast[];
  notifySuccess: (message: string) => void;
  notifyError: (error: unknown, fallback: string) => void;
  notifyPermissionDenied: (message?: string) => void;
  dismissToast: (id: string) => void;
};

const CompanyToastContext = createContext<CompanyToastContextValue | null>(null);

function toastId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `toast-${Date.now()}`;
}

export function CompanyToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<CompanyToast[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const pushToast = useCallback(
    (tone: CompanyToastTone, message: string) => {
      const id = toastId();
      setToasts((current) => [...current.slice(-4), { id, tone, message }]);
      window.setTimeout(() => dismissToast(id), tone === 'error' || tone === 'permission' ? 8000 : 5000);
    },
    [dismissToast],
  );

  const notifySuccess = useCallback((message: string) => pushToast('success', message), [pushToast]);
  const notifyError = useCallback(
    (error: unknown, fallback: string) => {
      if (error instanceof ApiError) {
        if (error.status === 403) {
          pushToast('permission', error.message);
          return;
        }
        pushToast('error', error.message || fallback);
        return;
      }
      pushToast('error', fallback);
    },
    [pushToast],
  );
  const notifyPermissionDenied = useCallback(
    (message = 'You do not have permission to perform this action.') => pushToast('permission', message),
    [pushToast],
  );

  const value = useMemo(
    () => ({ toasts, notifySuccess, notifyError, notifyPermissionDenied, dismissToast }),
    [toasts, notifySuccess, notifyError, notifyPermissionDenied, dismissToast],
  );

  return <CompanyToastContext.Provider value={value}>{children}</CompanyToastContext.Provider>;
}

export function useCompanyToast() {
  const context = useContext(CompanyToastContext);
  if (!context) {
    throw new Error('useCompanyToast must be used within CompanyToastProvider');
  }
  return context;
}

export function CompanyToastStack() {
  const { toasts, dismissToast } = useCompanyToast();
  if (toasts.length === 0) {
    return null;
  }
  return (
    <div className="admin-toast-stack" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`admin-toast admin-toast--${toast.tone}`}>
          <span>{toast.message}</span>
          <button type="button" className="admin-toast__dismiss" onClick={() => dismissToast(toast.id)}>
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
