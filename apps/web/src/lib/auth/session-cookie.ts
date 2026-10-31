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
  safeInternalPath as safeInternalPathImpl,
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

export function safeInternalPath(next: string | null | undefined, fallback = '/dashboard'): string {
  return safeInternalPathImpl(next, fallback);
}
