/**
 * Browser security headers for the Next.js staff/public web app.
 * Pure helpers — safe to import from middleware and tests.
 */

export const REFERRER_POLICY = 'strict-origin-when-cross-origin';
export const NOSNIFF = 'nosniff';
export const FRAME_OPTIONS = 'DENY';
export const HSTS_VALUE = 'max-age=31536000';
export const PERMISSIONS_POLICY = [
  'accelerometer=()',
  'autoplay=()',
  'camera=()',
  'display-capture=()',
  'geolocation=()',
  'gyroscope=()',
  'magnetometer=()',
  'microphone=()',
  'midi=()',
  'payment=()',
  'usb=()',
  'interest-cohort=()',
  'browsing-topics=()',
].join(', ');

const LOCAL_API_ORIGINS = ['http://localhost:8000', 'http://127.0.0.1:8000'] as const;

export function apiOriginsFromEnv(apiUrl?: string | null): string[] {
  const origins = new Set<string>(LOCAL_API_ORIGINS);
  const raw = (apiUrl || '').trim();
  if (!raw) return [...origins];
  try {
    const url = new URL(raw);
    origins.add(url.origin);
    if (url.hostname === 'localhost') {
      const loopback = new URL(url.origin);
      loopback.hostname = '127.0.0.1';
      origins.add(loopback.origin);
    } else if (url.hostname === '127.0.0.1') {
      const named = new URL(url.origin);
      named.hostname = 'localhost';
      origins.add(named.origin);
    }
  } catch {
    return [...origins];
  }
  return [...origins];
}

export function shouldSendHsts(input: {
  protocol: string;
  forwardedProto?: string | null;
  cookieSecure?: boolean;
}): boolean {
  if (input.protocol === 'https:') return true;
  if (input.cookieSecure && input.forwardedProto === 'https') return true;
  return false;
}

export function createCspNonce(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
}

export function buildContentSecurityPolicy(nonce: string, options?: {
  isDev?: boolean;
  apiUrl?: string | null;
}): string {
  const api = apiOriginsFromEnv(options?.apiUrl).join(' ');
  const scriptSrc = options?.isDev
    ? `'self' 'nonce-${nonce}' 'unsafe-eval'`
    : `'self' 'nonce-${nonce}'`;
  const connectSrc = options?.isDev
    ? `'self' ${api} ws://localhost:3000 ws://127.0.0.1:3000`
    : `'self' ${api}`;

  return [
    "default-src 'self'",
    `script-src ${scriptSrc}`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' blob: data: ${api}`,
    "font-src 'self' data:",
    `connect-src ${connectSrc}`,
    `frame-src 'self' blob: ${api}`,
    "frame-ancestors 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "worker-src 'self' blob:",
    "manifest-src 'self'",
  ].join('; ');
}

export type HeaderMap = {
  set(name: string, value: string): void;
};

export function applySecurityHeaders(
  headers: HeaderMap,
  input: {
    nonce: string;
    protocol: string;
    forwardedProto?: string | null;
    cookieSecure?: boolean;
    isDev?: boolean;
    apiUrl?: string | null;
  },
): void {
  headers.set('Content-Security-Policy', buildContentSecurityPolicy(input.nonce, input));
  headers.set('X-Content-Type-Options', NOSNIFF);
  headers.set('Referrer-Policy', REFERRER_POLICY);
  headers.set('X-Frame-Options', FRAME_OPTIONS);
  headers.set('Permissions-Policy', PERMISSIONS_POLICY);
  if (shouldSendHsts(input)) {
    headers.set('Strict-Transport-Security', HSTS_VALUE);
  }
}
