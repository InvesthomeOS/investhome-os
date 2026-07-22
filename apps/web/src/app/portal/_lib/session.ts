import { createHmac, timingSafeEqual } from 'crypto';

import { PORTAL_DEMO_USERS } from '../_data/investors';
import type { PortalSessionPayload } from '../_data/types';

export const PORTAL_SESSION_COOKIE = 'ih_portal_session';

const DEV_FALLBACK_SECRET = 'dev-only-portal-session-secret-change-me';

function portalSessionSecret(): string {
  return (
    process.env.PORTAL_SESSION_SECRET ||
    process.env.JWT_SECRET ||
    (process.env.NODE_ENV === 'production' ? '' : DEV_FALLBACK_SECRET)
  );
}

function signPayload(payloadJson: string, secret: string): string {
  return createHmac('sha256', secret).update(payloadJson).digest('base64url');
}

/**
 * Encode a signed portal session cookie: base64url(json).base64url(hmac).
 * Unsigned legacy cookies are rejected by decodePortalSession.
 */
export function encodePortalSession(payload: PortalSessionPayload): string {
  const secret = portalSessionSecret();
  if (!secret) {
    throw new Error('PORTAL_SESSION_SECRET (or JWT_SECRET) is required in production');
  }
  const payloadJson = JSON.stringify(payload);
  const body = Buffer.from(payloadJson, 'utf8').toString('base64url');
  const sig = signPayload(payloadJson, secret);
  return `${body}.${sig}`;
}

export function decodePortalSession(raw: string | undefined | null): PortalSessionPayload | null {
  if (!raw) return null;
  const secret = portalSessionSecret();
  if (!secret) return null;
  try {
    const dot = raw.indexOf('.');
    if (dot <= 0) {
      // Reject unsigned legacy base64-only cookies (forgeable).
      return null;
    }
    const body = raw.slice(0, dot);
    const sig = raw.slice(dot + 1);
    if (!sig) return null;
    const payloadJson = Buffer.from(body, 'base64url').toString('utf8');
    const expected = signPayload(payloadJson, secret);
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
    const data = JSON.parse(payloadJson) as PortalSessionPayload;
    if (!data?.investorId || !data?.email) return null;
    return data;
  } catch {
    return null;
  }
}

export function authenticatePortalDemo(
  email: string,
  password: string,
): PortalSessionPayload | null {
  const match = PORTAL_DEMO_USERS.find(
    (u) => u.email.toLowerCase() === email.trim().toLowerCase() && u.password === password,
  );
  if (!match) return null;
  return {
    investorId: match.investorId,
    email: match.email,
    issuedAt: new Date().toISOString(),
  };
}
