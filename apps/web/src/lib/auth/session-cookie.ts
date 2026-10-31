/**
 * Edge-safe session gate for Next.js middleware.
 * Signing secret and cookie attributes come from server env, never NEXT_PUBLIC_.
 */

import {
  SESSION_COOKIE,
  absoluteSessionLifetimeMs,
  clearedSessionCookieOptions as clearedSessionCookieOptionsUntyped,
  dashboardSessionGate,
  getSessionJwtSecret,
  isValidSessionJwt,
} from './session-cookie.mjs';

export type ClearedSessionCookieOptions = {
  path: string;
  maxAge: number;
  httpOnly: boolean;
  secure: boolean;
  sameSite: 'lax' | 'strict' | 'none';
  domain?: string;
};

export function clearedSessionCookieOptions(
  env?: Record<string, string | undefined>,
): ClearedSessionCookieOptions {
  return clearedSessionCookieOptionsUntyped(env) as ClearedSessionCookieOptions;
}

export {
  SESSION_COOKIE,
  absoluteSessionLifetimeMs,
  dashboardSessionGate,
  getSessionJwtSecret,
  isValidSessionJwt,
};

const AUTH_ONLY_PREFIXES = ['/reset-password', '/invite', '/portal/login'] as const;

function isAuthOnlyPath(pathOnly: string): boolean {
  if (pathOnly.startsWith('/login')) return true;
  return AUTH_ONLY_PREFIXES.some((prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`));
}

export function safeInternalPath(next: string | null | undefined, fallback = '/dashboard'): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.includes('\\') || next.includes('://')) {
    return fallback;
  }
  const pathOnly = next.split('?')[0]?.split('#')[0] ?? next;
  if (pathOnly.split('/').includes('..') || isAuthOnlyPath(pathOnly)) return fallback;
  return next;
}
