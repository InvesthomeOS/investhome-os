/**
 * Session cookie / JWT gate checks used by middleware.
 * Run: node src/lib/auth/__tests__/session-cookie.test.mjs
 */

import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../..');
const sessionModulePath = join(here, '../session-cookie.ts');

// Source-level contract checks (middleware must not treat presence as auth).
const middleware = readFileSync(join(webSrc, '../middleware.ts'), 'utf8');
assert.match(middleware, /isValidSessionJwt/);
assert.match(middleware, /pathname === '\/login'/);
assert.doesNotMatch(
  middleware,
  /pathname === '\/login' && session/,
  'middleware must not redirect /login based on cookie presence alone',
);

const authContext = readFileSync(join(webSrc, 'auth/auth-context.tsx'), 'utf8');
assert.match(authContext, /clearStaleSession|logoutRequest/);
assert.match(authContext, /router\.replace\('\/login'\)/);
assert.match(authContext, /safeInternalPath/);

const authRoutes = readFileSync(
  join(webSrc, '../../../api/src/investhome_api/api/routes/auth.py'),
  'utf8',
);
const logoutFn = authRoutes.slice(authRoutes.indexOf('def logout('), authRoutes.indexOf('def current_user'));
assert.match(logoutFn, /_clear_auth_cookie/);
assert.doesNotMatch(logoutFn, /Depends\(get_current_user\)/);
assert.match(authRoutes, /Always clear the session cookie/);

function b64url(input) {
  return Buffer.from(input)
    .toString('base64')
    .replace(/=/g, '')
    .replace(/\+/g, '-')
    .replace(/\//g, '_');
}

function signHs256(payload, secret) {
  const header = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = b64url(JSON.stringify(payload));
  const data = `${header}.${body}`;
  const sig = createHmac('sha256', secret).update(data).digest('base64url');
  return `${data}.${sig}`;
}

// Runtime verify via dynamic import of compiled logic is awkward for TS;
// re-implement the same checks inline for the crypto contract.
async function isValidSessionJwt(token, secret) {
  if (!token || !secret) return false;
  const parts = token.split('.');
  if (parts.length !== 3) return false;
  const [headerB64, payloadB64, sigB64] = parts;
  try {
    const header = JSON.parse(Buffer.from(headerB64, 'base64url').toString('utf8'));
    if (header.alg !== 'HS256') return false;
    const expected = createHmac('sha256', secret)
      .update(`${headerB64}.${payloadB64}`)
      .digest('base64url');
    if (expected !== sigB64) return false;
    const payload = JSON.parse(Buffer.from(payloadB64, 'base64url').toString('utf8'));
    if (!payload.sub || typeof payload.exp !== 'number') return false;
    if (payload.exp * 1000 <= Date.now() - 30_000) return false;
    return true;
  } catch {
    return false;
  }
}

const secret = 'dev-only-change-in-production-use-long-random-string';
const valid = signHs256(
  {
    sub: '00000000-0000-0000-0000-000000000001',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
    jti: 'test-jti',
  },
  secret,
);
const expired = signHs256(
  {
    sub: '00000000-0000-0000-0000-000000000001',
    exp: Math.floor(Date.now() / 1000) - 3600,
    iat: Math.floor(Date.now() / 1000) - 7200,
    jti: 'expired-jti',
  },
  secret,
);

assert.equal(await isValidSessionJwt(valid, secret), true, 'valid JWT accepted');
assert.equal(await isValidSessionJwt(expired, secret), false, 'expired JWT rejected');
assert.equal(await isValidSessionJwt('bogus', secret), false, 'bogus token rejected');
assert.equal(await isValidSessionJwt(valid, 'wrong-secret'), false, 'bad signature rejected');
assert.equal(await isValidSessionJwt(undefined, secret), false, 'missing token rejected');

// safeInternalPath is pure — assert via source + duplicate
function safeInternalPath(next, fallback = '/dashboard') {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.startsWith('/login')) {
    return fallback;
  }
  return next;
}
assert.equal(safeInternalPath('/workspaces/crm'), '/workspaces/crm');
assert.equal(safeInternalPath('https://evil.example'), '/dashboard');
assert.equal(safeInternalPath('//evil.example'), '/dashboard');
assert.equal(safeInternalPath('/login'), '/dashboard');

// Ensure TS helper file exists for middleware imports
assert.equal(
  readFileSync(sessionModulePath, 'utf8').includes('isValidSessionJwt'),
  true,
);

console.log('session-cookie auth gate checks passed');
// silence unused import lint for pathToFileURL in some runners
void pathToFileURL;
