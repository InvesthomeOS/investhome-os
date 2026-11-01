/**
 * ih_session cookie and post-login path helpers.
 * The API is the only session validator. Middleware asks GET /auth/me.
 * NEXT_PUBLIC_API_URL is the public API origin, not a secret.
 */

export const SESSION_COOKIE = 'ih_session';

const AUTH_ME_PATH = '/auth/me';
const DEFAULT_API_BASE = 'http://localhost:8000';
const DEFAULT_TIMEOUT_MS = 5000;

function runtimeSessionEnv() {
  return {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    AUTH_COOKIE_DOMAIN: process.env.AUTH_COOKIE_DOMAIN,
    AUTH_COOKIE_SECURE: process.env.AUTH_COOKIE_SECURE,
    AUTH_COOKIE_SAMESITE: process.env.AUTH_COOKIE_SAMESITE,
  };
}

function textValue(value) {
  return typeof value === 'string' ? value.trim() : '';
}

/**
 * @param {Record<string, string | undefined>=} env
 * @returns {string}
 */
export function sessionApiBaseUrl(env = runtimeSessionEnv()) {
  const configured = textValue(env.NEXT_PUBLIC_API_URL);
  return (configured || DEFAULT_API_BASE).replace(/\/$/, '');
}

/**
 * @param {Record<string, string | undefined>=} env
 * @returns {{
 *   path: string,
 *   maxAge: number,
 *   httpOnly: true,
 *   secure: boolean,
 *   sameSite: 'lax' | 'strict' | 'none',
 *   domain?: string,
 * }}
 */
export function clearedSessionCookieOptions(env = runtimeSessionEnv()) {
  const domain = textValue(env.AUTH_COOKIE_DOMAIN);
  const sameRaw = textValue(env.AUTH_COOKIE_SAMESITE).toLowerCase() || 'lax';
  const sameSite = sameRaw === 'strict' || sameRaw === 'none' ? sameRaw : 'lax';
  const options = {
    path: '/',
    maxAge: 0,
    httpOnly: true,
    secure: env.AUTH_COOKIE_SECURE === 'true',
    sameSite,
  };
  if (domain) options.domain = domain;
  return options;
}

function decision(allow, redirect, clearCookie, unavailable) {
  return { allow, redirect, clearCookie, unavailable };
}

/**
 * Cookie presence only decides whether to ask the API.
 * 200 allows. 401/403 clears. Timeout, network failure, and 5xx keep the cookie.
 * @param {string | null | undefined} token
 * @param {{
 *   env?: Record<string, string | undefined>,
 *   fetchImpl?: typeof fetch,
 *   timeoutMs?: number,
 * }=} options
 */
export async function authorizeStaffSession(token, options = {}) {
  if (!token) return decision(false, '/login', false, false);
  const env = options.env ?? runtimeSessionEnv();
  const fetchImpl = options.fetchImpl ?? fetch;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const url = `${sessionApiBaseUrl(env)}${AUTH_ME_PATH}`;
  const timeout = AbortSignal.timeout(timeoutMs);
  try {
    const response = await fetchImpl(url, {
      method: 'GET',
      headers: {
        accept: 'application/json',
        cookie: `${SESSION_COOKIE}=${token}`,
      },
      cache: 'no-store',
      redirect: 'manual',
      credentials: 'omit',
      signal: timeout,
    });
    if (response.status === 200) return decision(true, null, false, false);
    if (response.status === 401 || response.status === 403) return decision(false, '/login', true, false);
    return decision(false, null, false, true);
  } catch {
    return decision(false, null, false, true);
  }
}

const AUTH_ONLY_PREFIXES = ['/reset-password', '/invite', '/portal/login'];

function isAuthOnlyPath(pathOnly) {
  if (pathOnly.startsWith('/login')) return true;
  return AUTH_ONLY_PREFIXES.some((prefix) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`));
}

/**
 * Next.js production webpack resolves ".mjs" before ".ts" for an extensionless
 * specifier, so this named export is the runtime contract the login page calls.
 * @param {string | null | undefined} next
 * @param {string} [fallback]
 * @returns {string}
 */
export function safeInternalPath(next, fallback = '/dashboard') {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.includes('\\') || next.includes('://')) {
    return fallback;
  }
  const pathOnly = next.split('?')[0]?.split('#')[0] ?? next;
  if (pathOnly.split('/').includes('..') || isAuthOnlyPath(pathOnly)) return fallback;
  return next;
}
