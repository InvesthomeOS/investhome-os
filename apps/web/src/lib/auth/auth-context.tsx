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
  updateUser,
  type CurrentUser,
} from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import type { AppLocale } from '@/i18n/config';
import { readLocaleCookie, resolveClientLocale, writeLocaleCookie } from '@/lib/i18n/locale-cookie';

type AuthContextValue = {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setPreferredLocale: (locale: AppLocale) => Promise<void>;
  hasPermission: (resource: string, action: string) => boolean;
  canViewAdmin: boolean;
  canManageUsers: boolean;
  canManageRoles: boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function applyLocaleFromUser(preferredLanguage?: string | null) {
  // Precedence: existing cookie (explicit selection) wins over preferred_language.
  const resolved = resolveClientLocale(preferredLanguage);
  if (resolved && !readLocaleCookie()) {
    writeLocaleCookie(resolved);
  }
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
      applyLocaleFromUser(current.preferred_language);
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
      // Keep explicit cookie if present; otherwise seed from profile preference.
      applyLocaleFromUser(current.preferred_language);
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

  const setPreferredLocale = useCallback(
    async (locale: AppLocale) => {
      writeLocaleCookie(locale);
      if (user?.id) {
        try {
          const updated = await updateUser(user.id, { preferred_language: locale });
          setUser((prev) =>
            prev
              ? {
                  ...prev,
                  preferred_language: updated.preferred_language ?? locale,
                }
              : prev,
          );
        } catch {
          // Cookie already updated; profile sync is best-effort.
        }
      }
    },
    [user?.id],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      login,
      logout,
      refresh,
      setPreferredLocale,
      hasPermission: (resource, action) => hasPermission(user, resource, action),
      canViewAdmin:
        canViewUsers(user) ||
        canViewRoles(user) ||
        (user?.permissions.includes('security:view') ?? false) ||
        (user?.permissions.includes('*:*') ?? false),
      canManageUsers: canManageUsers(user),
      canManageRoles: canManageRoles(user),
    }),
    [user, loading, error, login, logout, refresh, setPreferredLocale],
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
