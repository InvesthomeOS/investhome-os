/**
 * Session cookie / JWT gate checks used by middleware.
 * Run: node src/lib/auth/__tests__/session-cookie.test.mjs
 */

import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  clearedSessionCookieOptions,
  dashboardSessionGate,
  isValidSessionJwt,
} from '../session-cookie.mjs';
import { planLoginRedirect } from '../mfa-flow.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../..');
const sessionModulePath = join(here, '../session-cookie.mjs');

// Source-level contract checks (middleware must not treat presence as auth).
const middleware = readFileSync(join(webSrc, '../middleware.ts'), 'utf8');
assert.match(middleware, /isValidSessionJwt/);
assert.match(middleware, /clearedSessionCookieOptions/);
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

const secret = 'unit-test-jwt-secret-not-for-production-32';
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

const pastAbsolute = signHs256(
  {
    sub: '00000000-0000-0000-0000-000000000001',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
    auth_time: Math.floor(Date.now() / 1000) - 25 * 60 * 60,
    jti: 'past-absolute-jti',
  },
  secret,
);

assert.equal(await isValidSessionJwt(valid, secret), true, 'valid JWT accepted');
assert.equal(await isValidSessionJwt(expired, secret), false, 'expired JWT rejected');
assert.equal(await isValidSessionJwt(pastAbsolute, secret), false, 'absolute lifetime rejected');
const missingJti = signHs256(
  {
    sub: '00000000-0000-0000-0000-000000000001',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
  },
  secret,
);
const emptyJti = signHs256(
  {
    sub: '00000000-0000-0000-0000-000000000001',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
    jti: '',
  },
  secret,
);
assert.equal(await isValidSessionJwt(missingJti, secret), false, 'missing jti rejected');
assert.equal(await isValidSessionJwt(emptyJti, secret), false, 'empty jti rejected');
assert.equal(await isValidSessionJwt('bogus', secret), false, 'bogus token rejected');
assert.equal(await isValidSessionJwt(valid, 'wrong-secret'), false, 'bad signature rejected');
assert.equal(await isValidSessionJwt(undefined, secret), false, 'missing token rejected');

assert.equal(
  readFileSync(sessionModulePath, 'utf8').includes('jti'),
  true,
  'edge JWT check must require jti',
);
assert.equal(
  readFileSync(sessionModulePath, 'utf8').includes('auth_time'),
  true,
  'edge JWT check must enforce auth_time absolute lifetime',
);
assert.match(authContext, /err\.status === 401/);
assert.match(authContext, /clearStaleSession/);

// Production webpack resolves ".mjs" before ".ts". The login page imports
// `safeInternalPath` from `@/lib/auth/session-cookie` with no extension.
const NEXT_PRODUCTION_EXTENSIONS = ['.js', '.mjs', '.tsx', '.ts', '.jsx'];
function resolveLikeNextProduction(basePath) {
  for (const ext of NEXT_PRODUCTION_EXTENSIONS) {
    const candidate = `${basePath}${ext}`;
    if (existsSync(candidate)) return candidate;
  }
  throw new Error(`unresolved ${basePath}`);
}
const loginImportPath = resolveLikeNextProduction(join(here, '../session-cookie'));
assert.match(loginImportPath, /\.mjs$/, 'production resolves session-cookie.mjs before session-cookie.ts');
const loginSessionModule = await import(pathToFileURL(loginImportPath).href);
assert.equal(typeof loginSessionModule.safeInternalPath, 'function');
const { safeInternalPath } = loginSessionModule;
assert.equal(safeInternalPath('/workspaces/crm'), '/workspaces/crm');
assert.equal(safeInternalPath('/dashboard/projects'), '/dashboard/projects');
assert.equal(safeInternalPath('https://evil.example'), '/dashboard');
assert.equal(safeInternalPath('//evil.example'), '/dashboard');
assert.equal(safeInternalPath('/login'), '/dashboard');
assert.equal(safeInternalPath('/login/mfa'), '/dashboard');
assert.equal(safeInternalPath('/reset-password'), '/dashboard');
assert.equal(safeInternalPath('/invite/token'), '/dashboard');
assert.equal(safeInternalPath('/portal/login'), '/dashboard');
assert.equal(safeInternalPath('/dashboard/../login'), '/dashboard');
assert.equal(safeInternalPath(null), '/dashboard');

const pathSource = readFileSync(sessionModulePath, 'utf8');
assert.match(pathSource, /export function safeInternalPath/);
assert.match(pathSource, /function isAuthOnlyPath/);
assert.match(pathSource, /\/reset-password/);
assert.match(pathSource, /\/invite/);
assert.match(pathSource, /\/portal\/login/);

const loginPageSource = readFileSync(join(webSrc, '../app/login/page.tsx'), 'utf8');
assert.match(loginPageSource, /import \{ safeInternalPath \} from '@\/lib\/auth\/session-cookie'/);

const apiShaped = signHs256(
  {
    sub: '00000000-0000-0000-0000-000000000001',
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
    auth_time: Math.floor(Date.now() / 1000),
    jti: 'abcdef0123456789abcdef0123456789',
  },
  secret,
);
const accepted = await dashboardSessionGate(apiShaped, secret);
assert.equal(accepted.allow, true, 'API-shaped HS256 session is accepted');
assert.equal(accepted.redirect, null);
assert.equal(accepted.clearCookie, false);
const anonymous = await dashboardSessionGate(undefined, secret);
assert.equal(anonymous.allow, false, 'anonymous dashboard request is blocked');
assert.equal(anonymous.redirect, '/login');
assert.equal(anonymous.clearCookie, false);
const forged = await dashboardSessionGate(apiShaped, 'wrong-secret-not-the-api-secret-32xx');
assert.equal(forged.allow, false, 'invalid signature is rejected');
assert.equal(forged.clearCookie, true);
const stale = await dashboardSessionGate(expired, secret);
assert.equal(stale.allow, false, 'expired session is rejected');
assert.equal(stale.clearCookie, true);

const cleared = clearedSessionCookieOptions({
  AUTH_COOKIE_DOMAIN: 'os.investhome.com',
  AUTH_COOKIE_SECURE: 'true',
  AUTH_COOKIE_SAMESITE: 'lax',
});
assert.equal(cleared.domain, 'os.investhome.com');
assert.equal(cleared.path, '/');
assert.equal(cleared.maxAge, 0);
assert.equal(cleared.httpOnly, true);
assert.equal(cleared.secure, true);
assert.equal(cleared.sameSite, 'lax');

const sessionSource = readFileSync(sessionModulePath, 'utf8');
assert.match(sessionSource, /process\.env\.JWT_SECRET/);
assert.match(sessionSource, /isValidSessionJwt/);
assert.match(sessionSource, /process\.env\.AUTH_COOKIE_DOMAIN/);
assert.match(sessionSource, /process\.env\.AUTH_COOKIE_SECURE/);
assert.match(sessionSource, /process\.env\.SESSION_ABSOLUTE_TIMEOUT_MINUTES/);
assert.doesNotMatch(sessionSource, /process\.env\[/);
assert.equal(sessionSource.includes('dev-only-change-in-production'), false);

const repoRoot = join(here, '../../../../../..');
const prodCompose = readFileSync(join(repoRoot, 'docker-compose.prod.yml'), 'utf8');
const webService = prodCompose.slice(prodCompose.indexOf('\n  web:'), prodCompose.indexOf('\n  caddy:'));
const apiEnv = prodCompose.slice(prodCompose.indexOf('x-app-environment:'), prodCompose.indexOf('\n  web:'));
assert.match(webService, /JWT_SECRET:/);
assert.match(webService, /AUTH_COOKIE_DOMAIN: "os\.investhome\.com"/);
assert.match(apiEnv, /JWT_SECRET:/);
assert.match(apiEnv, /AUTH_COOKIE_DOMAIN: "os\.investhome\.com"/);

const loginPage = readFileSync(join(webSrc, '../app/login/page.tsx'), 'utf8');
assert.doesNotMatch(loginPage, /window\.location\.replace/);
assert.doesNotMatch(loginPage, /router\.refresh\(\)/);
const redirect = planLoginRedirect({
  view: {
    pathname: '/login',
    user: { id: '00000000-0000-0000-0000-000000000001', email: 'sales@investhome.demo' },
    mfaPending: null,
    enrollmentPending: null,
    nextPath: null,
  },
  started: false,
});
assert.equal(redirect.action, 'router.replace');
assert.equal(redirect.href, '/dashboard');
assert.equal(redirect.document, false);
const settled = planLoginRedirect({
  view: {
    pathname: '/dashboard',
    user: { id: '00000000-0000-0000-0000-000000000001', email: 'sales@investhome.demo' },
    mfaPending: null,
    enrollmentPending: null,
    nextPath: null,
  },
  started: true,
});
assert.equal(settled.action, 'stay');
assert.notEqual(settled.pathname, '/login');

console.log('session-cookie auth gate checks passed');
// silence unused import lint for pathToFileURL in some runners
void pathToFileURL;
