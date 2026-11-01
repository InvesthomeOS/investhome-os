/**
 * Staff session gate. The API validates ih_session. This module only asks
 * GET /auth/me and describes how to clear the cookie.
 */

import {
  SESSION_COOKIE,
  authorizeStaffSession as authorizeStaffSessionImpl,
  clearedSessionCookieOptions as clearedSessionCookieOptionsUntyped,
  safeInternalPath as safeInternalPathImpl,
  sessionApiBaseUrl as sessionApiBaseUrlImpl,
} from './session-cookie.mjs';

export type ClearedSessionCookieOptions = {
  path: string;
  maxAge: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: 'lax' | 'strict' | 'none';
  domain?: string;
};

export type StaffSessionDecision = {
  allow: boolean;
  redirect: string | null;
  clearCookie: boolean;
  unavailable: boolean;
};

export function clearedSessionCookieOptions(
  env?: Record<string, string | undefined>,
): ClearedSessionCookieOptions {
  return clearedSessionCookieOptionsUntyped(env) as ClearedSessionCookieOptions;
}

export function sessionApiBaseUrl(env?: Record<string, string | undefined>): string {
  if (!env) return sessionApiBaseUrlImpl();
  return sessionApiBaseUrlImpl({
    NEXT_PUBLIC_API_URL: env.NEXT_PUBLIC_API_URL,
    AUTH_COOKIE_DOMAIN: env.AUTH_COOKIE_DOMAIN,
    AUTH_COOKIE_SECURE: env.AUTH_COOKIE_SECURE,
    AUTH_COOKIE_SAMESITE: env.AUTH_COOKIE_SAMESITE,
  });
}

export async function authorizeStaffSession(
  token: string | null | undefined,
  options?: {
    env?: Record<string, string | undefined>;
    fetchImpl?: typeof fetch;
    timeoutMs?: number;
  },
): Promise<StaffSessionDecision> {
  return authorizeStaffSessionImpl(token, options) as Promise<StaffSessionDecision>;
}

export function safeInternalPath(next: string | null | undefined, fallback = '/dashboard'): string {
  return safeInternalPathImpl(next, fallback);
}

export { SESSION_COOKIE };
