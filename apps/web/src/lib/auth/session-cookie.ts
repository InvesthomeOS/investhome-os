/**
 * Edge-safe JWT session checks for Next.js middleware.
 * Uses the same HS256 secret as the API (`JWT_SECRET`).
 */

export const SESSION_COOKIE = 'ih_session';

/**
 * Read env without direct `process.env.JWT_SECRET` access.
 * Next.js may inline direct `process.env.X` at build time; bracket access keeps
 * self-hosted Docker runtime secrets working in Edge middleware.
 */
function readRuntimeEnv(name: string): string {
  try {
    const value = process.env[name];
    return typeof value === 'string' ? value : '';
  } catch {
    return '';
  }
}

export function getSessionJwtSecret(): string {
  return readRuntimeEnv('JWT_SECRET').trim();
}

function base64UrlToBytes(input: string): Uint8Array {
  const padded = input.replace(/-/g, '+').replace(/_/g, '/');
  const pad = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4));
  const binary = atob(padded + pad);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Verify ih_session JWT signature + expiry (not DB revocation).
 * Middleware gate only — API remains source of truth for /auth/me.
 */
export async function isValidSessionJwt(
  token: string | undefined | null,
  secret: string = getSessionJwtSecret(),
): Promise<boolean> {
  if (!token || !secret) return false;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  const [headerB64, payloadB64, sigB64] = parts;
  if (!headerB64 || !payloadB64 || !sigB64) return false;

  try {
    const headerJson = new TextDecoder().decode(base64UrlToBytes(headerB64));
    const header = JSON.parse(headerJson) as { alg?: string };
    if (header.alg !== 'HS256') return false;

    const key = await crypto.subtle.importKey(
      'raw',
      new TextEncoder().encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify'],
    );
    const data = new TextEncoder().encode(`${headerB64}.${payloadB64}`);
    const signature = base64UrlToBytes(sigB64);
    const valid = await crypto.subtle.verify('HMAC', key, signature, data);
    if (!valid) return false;

    const payloadJson = new TextDecoder().decode(base64UrlToBytes(payloadB64));
    const payload = JSON.parse(payloadJson) as {
      sub?: string;
      exp?: number;
      jti?: string;
      auth_time?: number;
    };
    if (!payload.sub || typeof payload.exp !== 'number') return false;
    if (typeof payload.jti !== 'string' || !/^[A-Za-z0-9._-]{1,64}$/.test(payload.jti.trim())) {
      return false;
    }
    // Small clock skew allowance (30s)
    if (payload.exp * 1000 <= Date.now() - 30_000) return false;
    // Absolute lifetime from original login (24h). API also enforces this via session.created_at.
    if (typeof payload.auth_time === 'number') {
      const absoluteMs = 24 * 60 * 60 * 1000;
      if (payload.auth_time * 1000 + absoluteMs <= Date.now() - 30_000) return false;
    }
    return true;
  } catch {
    return false;
  }
}

export function safeInternalPath(next: string | null | undefined, fallback = '/dashboard'): string {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/login')) {
    return fallback;
  }
  return next;
}
