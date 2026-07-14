'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  canManageRoles,
  canManageUsers,
  canViewRoles,
  canViewUsers,
  fetchCurrentUser,
  hasPermission,
  login as loginRequest,
  logout as logoutRequest,
  type CurrentUser,
} from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import { LOCALE_COOKIE, type AppLocale } from '@/i18n/config';

type AuthContextValue = {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hasPermission: (resource: string, action: string) => boolean;
  canViewAdmin: boolean;
  canManageUsers: boolean;
  canManageRoles: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function setLocaleCookie(locale: AppLocale) {
  document.cookie = `${LOCALE_COOKIE}=${locale};path=/;max-age=${60 * 60 * 24 * 365};samesite=lax`;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const current = await fetchCurrentUser();
      setUser(current);
      if (current.preferred_language === 'tr' || current.preferred_language === 'en') {
        setLocaleCookie(current.preferred_language);
      }
    } catch (err) {
      setUser(null);
      if (err instanceof ApiError && err.status === 401) {
        setError(null);
      } else {
        setError(err instanceof Error ? err.message : 'Unable to load session');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const current = await loginRequest(email, password);
      setUser(current);
      if (current.preferred_language === 'tr' || current.preferred_language === 'en') {
        setLocaleCookie(current.preferred_language);
      }
      router.push('/dashboard');
      router.refresh();
    },
    [router],
  );

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } finally {
      setUser(null);
      router.push('/login');
      router.refresh();
    }
  }, [router]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      login,
      logout,
      refresh,
      hasPermission: (resource, action) => hasPermission(user, resource, action),
      canViewAdmin: canViewUsers(user) || canViewRoles(user),
      canManageUsers: canManageUsers(user),
      canManageRoles: canManageRoles(user),
    }),
    [user, loading, error, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
