/**
 * Edge-safe portal session checks for Next.js middleware.
 * Cookie format matches encodePortalSession: base64url(json).base64url(hmac-sha256(json)).
 */

export const PORTAL_SESSION_COOKIE = 'ih_portal_session';

/** Matches portal session cookie maxAge (12 hours). */
export const PORTAL_SESSION_TTL_SECONDS = 60 * 60 * 12;

const CLOCK_SKEW_MS = 30_000;

function readRuntimeEnv(name) {
  try {
    const value = process.env[name];
    return typeof value === 'string' ? value : '';
  } catch {
    return '';
  }
}

export function getPortalSessionSecret() {
  return readRuntimeEnv('PORTAL_SESSION_SECRET').trim();
}

function base64UrlToBytes(input) {
  const padded = input.replace(/-/g, '+').replace(/_/g, '/');
  const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4));
  const binary = atob(padded + pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function hasExpectedPortalSessionStructure(data) {
  return Boolean(
    data &&
      typeof data === 'object' &&
      typeof data.investorId === 'string' &&
      data.investorId.length > 0 &&
      typeof data.email === 'string' &&
      data.email.length > 0 &&
      typeof data.issuedAt === 'string' &&
      data.issuedAt.length > 0,
  );
}

export function isPortalSessionExpired(issuedAt, nowMs = Date.now()) {
  const issued = Date.parse(issuedAt);
  if (!Number.isFinite(issued)) return true;
  if (issued > nowMs + CLOCK_SKEW_MS) return true;
  return issued + PORTAL_SESSION_TTL_SECONDS * 1000 <= nowMs - CLOCK_SKEW_MS;
}

/**
 * Verify portal cookie signature, expiry, and payload shape.
 * Middleware gate only — does not log or return why validation failed.
 */
export async function isValidPortalSession(raw, secret = getPortalSessionSecret()) {
  if (!raw || !secret) return false;
  const dot = raw.indexOf('.');
  if (dot <= 0) return false;
  const body = raw.slice(0, dot);
  const sig = raw.slice(dot + 1);
  if (!body || !sig) return false;

  try {
    const payloadJson = new TextDecoder().decode(base64UrlToBytes(body));
    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify'],
    );
    const valid = await crypto.subtle.verify(
      'HMAC',
      key,
      base64UrlToBytes(sig),
      new TextEncoder().encode(payloadJson),
    );
    if (!valid) return false;

    const data = JSON.parse(payloadJson);
    if (!hasExpectedPortalSessionStructure(data)) return false;
    if (isPortalSessionExpired(data.issuedAt)) return false;
    return true;
  } catch {
    return false;
  }
}

export function portalAccessDecision(pathname, sessionValid) {
  if (pathname !== '/portal' && !pathname.startsWith('/portal/')) {
    return 'next';
  }
  const isLogin = pathname === '/portal/login' || pathname.startsWith('/portal/login/');
  if (!sessionValid && !isLogin) return 'redirect-login';
  if (sessionValid && isLogin) return 'redirect-home';
  return 'next';
}

const PORTAL_HOME = '/portal';

function decodeUntilStable(value) {
  let current = value;
  for (let i = 0; i < 8; i += 1) {
    let decoded;
    try {
      decoded = decodeURIComponent(current.replace(/\+/g, '%20'));
    } catch {
      return null;
    }
    if (decoded === current) return current;
    current = decoded;
  }
  return null;
}

/**
 * Allow only same-origin portal paths. External, protocol-relative, and
 * non-portal destinations fall back to /portal.
 */
export function safePortalPath(next, fallback = PORTAL_HOME) {
  if (typeof next !== 'string' || !next) return fallback;
  if (/[\u0000-\u001F\u007F]/.test(next)) return fallback;

  const decoded = decodeUntilStable(next.trim());
  if (decoded == null) return fallback;
  const candidate = decoded.trim();
  if (!candidate.startsWith('/') || candidate.startsWith('//')) return fallback;
  if (candidate.includes('\\') || candidate.includes(':') || candidate.includes('@')) return fallback;

  try {
    const url = new URL(candidate, 'https://investhome.invalid');
    if (url.protocol !== 'https:' || url.host !== 'investhome.invalid') return fallback;
    if (url.username || url.password) return fallback;
    const path = url.pathname;
    if (path !== '/portal' && !path.startsWith('/portal/')) return fallback;
    if (path.includes(':') || path.includes('\\') || path.includes('//')) return fallback;
    return path + url.search;
  } catch {
    return fallback;
  }
}
