/**
 * Shared ih_session gate. API signs HS256 with JWT_SECRET and claims
 * sub, exp, iat, jti, auth_time. No issuer or audience.
 *
 * Static process.env.NAME reads are required so the Next.js Edge middleware
 * manifest receives these server-only names and the running server fills them.
 * Do not read them dynamically, and do not copy them into NEXT_PUBLIC_ vars.
 */

export const SESSION_COOKIE = 'ih_session';

const DEFAULT_ABSOLUTE_MINUTES = 1440;
const CLOCK_SKEW_MS = 30_000;

function runtimeSessionEnv() {
  return {
    JWT_SECRET: process.env.JWT_SECRET,
    AUTH_COOKIE_DOMAIN: process.env.AUTH_COOKIE_DOMAIN,
    AUTH_COOKIE_SECURE: process.env.AUTH_COOKIE_SECURE,
    AUTH_COOKIE_SAMESITE: process.env.AUTH_COOKIE_SAMESITE,
    SESSION_ABSOLUTE_TIMEOUT_MINUTES: process.env.SESSION_ABSOLUTE_TIMEOUT_MINUTES,
  };
}

function textValue(value) {
  return typeof value === 'string' ? value.trim() : '';
}

export function getSessionJwtSecret(env = runtimeSessionEnv()) {
  return textValue(env.JWT_SECRET);
}

export function absoluteSessionLifetimeMs(env = runtimeSessionEnv()) {
  const parsed = Number(textValue(env.SESSION_ABSOLUTE_TIMEOUT_MINUTES));
  const minutes = Number.isFinite(parsed) && parsed >= 1 ? parsed : DEFAULT_ABSOLUTE_MINUTES;
  return minutes * 60 * 1000;
}

function bytesToBuffer(bytes) {
  const copy = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(copy).set(bytes);
  return copy;
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

export async function isValidSessionJwt(token, secret = getSessionJwtSecret(), env = runtimeSessionEnv()) {
  if (!token || !secret) return false;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  const [headerB64, payloadB64, sigB64] = parts;
  if (!headerB64 || !payloadB64 || !sigB64) return false;

  try {
    const header = JSON.parse(new TextDecoder().decode(base64UrlToBytes(headerB64)));
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
    const valid = await crypto.subtle.verify('HMAC', key, bytesToBuffer(signature), bytesToBuffer(data));
    if (!valid) return false;

    const payload = JSON.parse(new TextDecoder().decode(base64UrlToBytes(payloadB64)));
    if (!payload.sub || typeof payload.exp !== 'number') return false;
    if (typeof payload.jti !== 'string' || !/^[A-Za-z0-9._-]{1,64}$/.test(payload.jti.trim())) {
      return false;
    }
    if (payload.exp * 1000 <= Date.now() - CLOCK_SKEW_MS) return false;
    if (typeof payload.auth_time === 'number') {
      const absoluteMs = absoluteSessionLifetimeMs(env);
      if (payload.auth_time * 1000 + absoluteMs <= Date.now() - CLOCK_SKEW_MS) return false;
    }
    return true;
  } catch {
    return false;
  }
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

export async function dashboardSessionGate(token, secret = getSessionJwtSecret(), env = runtimeSessionEnv()) {
  const valid = await isValidSessionJwt(token, secret, env);
  if (valid) return { allow: true, redirect: null, clearCookie: false };
  return { allow: false, redirect: '/login', clearCookie: Boolean(token) };
}
