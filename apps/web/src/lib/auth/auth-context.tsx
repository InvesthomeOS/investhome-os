'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';

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
  verifyMfaLogin,
  type CurrentUser,
} from '@/lib/api/auth';
import { ApiError, ensureCsrfToken } from '@/lib/api/client';
import type { AppLocale } from '@/i18n/config';
import { readLocaleCookie, resolveClientLocale, writeLocaleCookie } from '@/lib/i18n/locale-cookie';
import { isCurrentUserResponse, isMfaChallengeResponse, isMfaEnrollmentRequiredResponse } from '@/lib/auth/mfa-flow';
import { safeInternalPath } from '@/lib/auth/session-cookie';

export type MfaPendingChallenge = {
  token: string;
  method: string;
  expiresIn: number;
  next: string | null;
};

export type MfaEnrollmentPending = {
  token: string;
  expiresIn: number;
  next: string | null;
};

type AuthContextValue = {
  user: CurrentUser | null;
  loading: boolean;
  error: string | null;
  mfaPending: MfaPendingChallenge | null;
  enrollmentPending: MfaEnrollmentPending | null;
  login: (email: string, password: string, options?: { next?: string | null }) => Promise<void>;
  completeMfaLogin: (code: string) => Promise<void>;
  cancelMfaLogin: () => void;
  finishRequiredEnrollment: (user: CurrentUser) => void;
  cancelEnrollment: () => void;
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
  const pathname = usePathname();
  const pathnameRef = useRef(pathname);
  pathnameRef.current = pathname;
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [mfaPending, setMfaPending] = useState<MfaPendingChallenge | null>(null);
  const [enrollmentPending, setEnrollmentPending] = useState<MfaEnrollmentPending | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const clearingSessionRef = useRef(false);

  const clearStaleSession = useCallback(async () => {
    if (clearingSessionRef.current) return;
    clearingSessionRef.current = true;
    try {
      await logoutRequest();
    } catch {
      // Best-effort cookie clear; API logout is designed to succeed even with a bad cookie.
    } finally {
      setUser(null);
      setError(null);
      const currentPath = pathnameRef.current;
      const onLogin = currentPath === '/login' || currentPath.startsWith('/login/');
      if (!onLogin) {
        router.replace('/login');
      }
      clearingSessionRef.current = false;
    }
  }, [router]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const current = await fetchCurrentUser();
      setUser(current);
      applyLocaleFromUser(current.preferred_language);
      void ensureCsrfToken();
    } catch (err) {
      setUser(null);
      if (err instanceof ApiError && err.status === 401) {
        await clearStaleSession();
      } else {
        setError(err instanceof Error ? err.message : 'Unable to load session');
      }
    } finally {
      setLoading(false);
    }
  }, [clearStaleSession]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string, options?: { next?: string | null }) => {
      setError(null);
      const result = await loginRequest(email, password);
      if (isMfaChallengeResponse(result)) {
        setUser(null);
        setEnrollmentPending(null);
        setMfaPending({
          token: result.mfa_challenge_token,
          method: result.mfa_method ?? 'totp',
          expiresIn: result.expires_in ?? 300,
          next: options?.next ?? null,
        });
        return;
      }
      if (isMfaEnrollmentRequiredResponse(result)) {
        setUser(null);
        setMfaPending(null);
        setEnrollmentPending({
          token: result.mfa_enrollment_challenge_token,
          expiresIn: result.expires_in ?? 300,
          next: options?.next ?? null,
        });
        return;
      }
      if (!isCurrentUserResponse(result)) {
        throw new ApiError('Sign in failed.', 500);
      }
      setMfaPending(null);
      setEnrollmentPending(null);
      setUser(result);
      applyLocaleFromUser(result.preferred_language);
      void ensureCsrfToken();
      router.replace(safeInternalPath(options?.next));
      router.refresh();
    },
    [router],
  );

  const completeMfaLogin = useCallback(
    async (code: string) => {
      if (!mfaPending) {
        throw new Error('mfa_challenge_missing');
      }
      const current = await verifyMfaLogin(mfaPending.token, code);
      if (!isCurrentUserResponse(current)) {
        throw new ApiError('Unable to verify. Please try again.', 500);
      }
      const next = mfaPending.next;
      setMfaPending(null);
      setUser(current);
      applyLocaleFromUser(current.preferred_language);
      void ensureCsrfToken();
      router.replace(safeInternalPath(next));
      router.refresh();
    },
    [mfaPending, router],
  );

  const cancelMfaLogin = useCallback(() => {
    setMfaPending(null);
    setEnrollmentPending(null);
  }, []);

  const finishRequiredEnrollment = useCallback(
    (current: CurrentUser) => {
      const next = enrollmentPending?.next ?? null;
      setEnrollmentPending(null);
      setMfaPending(null);
      setUser(current);
      applyLocaleFromUser(current.preferred_language);
      void ensureCsrfToken();
      router.replace(safeInternalPath(next));
      router.refresh();
    },
    [enrollmentPending, router],
  );

  const cancelEnrollment = useCallback(() => {
    setEnrollmentPending(null);
    setUser(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // Still clear client state and leave the app shell.
    } finally {
      setUser(null);
      setMfaPending(null);
      setEnrollmentPending(null);
      setError(null);
      router.replace('/login');
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
      mfaPending,
      enrollmentPending,
      login,
      completeMfaLogin,
      cancelMfaLogin,
      finishRequiredEnrollment,
      cancelEnrollment,
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
    [user, loading, error, mfaPending, enrollmentPending, login, completeMfaLogin, cancelMfaLogin, finishRequiredEnrollment, cancelEnrollment, logout, refresh, setPreferredLocale],
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

/**
 * Preview-only auth bridge for unauthenticated UX review routes.
 * Does not fetch or mutate session state. Production AuthProvider is unchanged.
 */
export function StaticAuthProvider({
  user,
  children,
}: {
  user: CurrentUser;
  children: React.ReactNode;
}) {
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading: false,
      error: null,
      mfaPending: null,
      enrollmentPending: null,
      login: async () => undefined,
      completeMfaLogin: async () => undefined,
      cancelMfaLogin: () => undefined,
      finishRequiredEnrollment: () => undefined,
      cancelEnrollment: () => undefined,
      logout: async () => undefined,
      refresh: async () => undefined,
      setPreferredLocale: async (locale: AppLocale) => {
        writeLocaleCookie(locale);
      },
      hasPermission: (resource, action) => hasPermission(user, resource, action),
      canViewAdmin: false,
      canManageUsers: false,
      canManageRoles: false,
    }),
    [user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
