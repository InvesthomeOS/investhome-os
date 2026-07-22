'use client';

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';

import { ApiError } from '@/lib/api/client';

export type AdminToastTone = 'success' | 'warning' | 'error' | 'permission';

export type AdminToast = {
  id: string;
  tone: AdminToastTone;
  message: string;
};

type AdminToastContextValue = {
  toasts: AdminToast[];
  pushToast: (tone: AdminToastTone, message: string) => void;
  dismissToast: (id: string) => void;
  notifySuccess: (message: string) => void;
  notifyWarning: (message: string) => void;
  notifyError: (error: unknown, fallback: string) => void;
  notifyPermissionDenied: (message?: string) => void;
};

const AdminToastContext = createContext<AdminToastContextValue | null>(null);

function toastId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `toast-${Date.now()}`;
}

export function AdminToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<AdminToast[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((current) => current.filter((item) => item.id !== id));
  }, []);

  const pushToast = useCallback((tone: AdminToastTone, message: string) => {
    const id = toastId();
    setToasts((current) => [...current.slice(-4), { id, tone, message }]);
    window.setTimeout(() => dismissToast(id), tone === 'error' || tone === 'permission' ? 8000 : 5000);
  }, [dismissToast]);

  const notifySuccess = useCallback(
    (message: string) => pushToast('success', message),
    [pushToast],
  );

  const notifyWarning = useCallback(
    (message: string) => pushToast('warning', message),
    [pushToast],
  );

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
    (message = 'You do not have permission to perform this action.') => {
      pushToast('permission', message);
    },
    [pushToast],
  );

  const value = useMemo(
    () => ({
      toasts,
      pushToast,
      dismissToast,
      notifySuccess,
      notifyWarning,
      notifyError,
      notifyPermissionDenied,
    }),
    [toasts, pushToast, dismissToast, notifySuccess, notifyWarning, notifyError, notifyPermissionDenied],
  );

  return <AdminToastContext.Provider value={value}>{children}</AdminToastContext.Provider>;
}

export function useAdminToast() {
  const context = useContext(AdminToastContext);
  if (!context) {
    throw new Error('useAdminToast must be used within AdminToastProvider');
  }
  return context;
}
