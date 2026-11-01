/**
 * Staff session gate. The API validates ih_session. Middleware only asks /auth/me.
 * Run: node src/lib/auth/__tests__/session-cookie.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import {
  authorizeStaffSession,
  clearedSessionCookieOptions,
  sessionApiBaseUrl,
} from '../session-cookie.mjs';
import { planLoginRedirect } from '../mfa-flow.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const webSrc = join(here, '../..');
const sessionModulePath = join(here, '../session-cookie.mjs');

const middleware = readFileSync(join(webSrc, '../middleware.ts'), 'utf8');
assert.match(middleware, /authorizeStaffSession\(session\)/);
assert.match(middleware, /clearedSessionCookieOptions/);
assert.match(middleware, /pathname === '\/login'/);
assert.match(middleware, /status: 503/);
assert.doesNotMatch(middleware, /isValidSessionJwt/);
assert.doesNotMatch(middleware, /JWT_SECRET/);
assert.doesNotMatch(
  middleware,
  /pathname === '\/login' && session/,
  'middleware must not redirect /login based on cookie presence alone',
);

const authContext = readFileSync(join(webSrc, 'auth/auth-context.tsx'), 'utf8');
assert.match(authContext, /clearStaleSession|logoutRequest/);
assert.match(authContext, /router\.replace\('\/login'\)/);
assert.match(authContext, /safeInternalPath/);
assert.match(authContext, /err\.status === 401/);
assert.match(authContext, /clearStaleSession/);
const successRefresh = authContext.slice(
  authContext.indexOf('const login ='),
  authContext.indexOf('const logout ='),
);
assert.doesNotMatch(successRefresh, /router\.refresh\(\)/);

const authRoutes = readFileSync(
  join(webSrc, '../../../api/src/investhome_api/api/routes/auth.py'),
  'utf8',
);
const logoutFn = authRoutes.slice(authRoutes.indexOf('def logout('), authRoutes.indexOf('def current_user'));
assert.match(logoutFn, /_clear_auth_cookie/);
assert.doesNotMatch(logoutFn, /Depends\(get_current_user\)/);
assert.match(authRoutes, /Always clear the session cookie/);
assert.match(authRoutes, /@router\.get\("\/me"/);

const env = {
  NEXT_PUBLIC_API_URL: 'https://api.investhome.example',
  AUTH_COOKIE_DOMAIN: 'os.investhome.com',
  AUTH_COOKIE_SECURE: 'true',
  AUTH_COOKIE_SAMESITE: 'lax',
};

function fakeFetch(status, fail = false) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url, init });
    if (fail) throw new Error('unavailable');
    return { status };
  };
  return { fetchImpl, calls };
}

const anonymous = await authorizeStaffSession(undefined, { env, fetchImpl: async () => { throw new Error('should not call'); } });
assert.equal(anonymous.allow, false, 'anonymous dashboard request is blocked');
assert.equal(anonymous.redirect, '/login');
assert.equal(anonymous.clearCookie, false);
assert.equal(anonymous.unavailable, false);

const acceptedFetch = fakeFetch(200);
const accepted = await authorizeStaffSession('api-issued-session', { env, fetchImpl: acceptedFetch.fetchImpl });
assert.equal(accepted.allow, true, 'API 200 allows the protected route');
assert.equal(accepted.redirect, null);
assert.equal(accepted.clearCookie, false);
assert.equal(acceptedFetch.calls.length, 1);
assert.equal(acceptedFetch.calls[0].url, 'https://api.investhome.example/auth/me');
assert.equal(acceptedFetch.calls[0].init.headers.cookie, 'ih_session=api-issued-session');
assert.equal(acceptedFetch.calls[0].init.redirect, 'manual');
assert.equal(acceptedFetch.calls[0].init.credentials, 'omit');

for (const status of [401, 403]) {
  const rejectedFetch = fakeFetch(status);
  const rejected = await authorizeStaffSession('rejected-session', { env, fetchImpl: rejectedFetch.fetchImpl });
  assert.equal(rejected.allow, false, `API ${status} rejects the session`);
  assert.equal(rejected.redirect, '/login');
  assert.equal(rejected.clearCookie, true, `API ${status} clears the cookie`);
  assert.equal(rejected.unavailable, false);
}

const serverError = await authorizeStaffSession('live-session', { env, fetchImpl: fakeFetch(500).fetchImpl });
assert.equal(serverError.allow, false);
assert.equal(serverError.redirect, null, 'API 500 does not redirect to login');
assert.equal(serverError.clearCookie, false, 'API 500 does not clear the session');
assert.equal(serverError.unavailable, true);

const down = await authorizeStaffSession('live-session', { env, fetchImpl: fakeFetch(0, true).fetchImpl });
assert.equal(down.clearCookie, false, 'an unavailable API does not clear the session');
assert.equal(down.redirect, null);
assert.equal(down.unavailable, true);

assert.equal(sessionApiBaseUrl({}), 'http://localhost:8000');
assert.equal(sessionApiBaseUrl({ NEXT_PUBLIC_API_URL: 'http://localhost:8000/' }), 'http://localhost:8000');

const NEXT_PRODUCTION_EXTENSIONS = ['.js', '.mjs', '.tsx', '.ts', '.jsx'];
function resolveLikeNextProduction(basePath) {
  for (const ext of NEXT_PRODUCTION_EXTENSIONS) {
    const candidate = `${basePath}${ext}`;
    if (existsSync(candidate)) return candidate;
  }
  throw new Error(`unresolved ${basePath}`);
}
const loginImportPath = resolveLikeNextProduction(join(here, '../session-cookie'));
assert.match(loginImportPath, /\.mjs$/);
const loginSessionModule = await import(pathToFileURL(loginImportPath).href);
assert.equal(typeof loginSessionModule.safeInternalPath, 'function');
assert.equal(typeof loginSessionModule.authorizeStaffSession, 'function');
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
assert.match(pathSource, /export async function authorizeStaffSession/);
assert.match(pathSource, /\/auth\/me/);
assert.match(pathSource, /function isAuthOnlyPath/);
assert.doesNotMatch(pathSource, /isValidSessionJwt/);
assert.doesNotMatch(pathSource, /JWT_SECRET/);
assert.match(pathSource, /process\.env\.NEXT_PUBLIC_API_URL/);
assert.match(pathSource, /process\.env\.AUTH_COOKIE_DOMAIN/);
assert.match(pathSource, /process\.env\.AUTH_COOKIE_SECURE/);
assert.doesNotMatch(pathSource, /process\.env\[/);

const cleared = clearedSessionCookieOptions(env);
assert.equal(cleared.domain, 'os.investhome.com');
assert.equal(cleared.path, '/');
assert.equal(cleared.maxAge, 0);
assert.equal(cleared.httpOnly, true);
assert.equal(cleared.secure, true);
assert.equal(cleared.sameSite, 'lax');

const repoRoot = join(here, '../../../../../..');
const prodCompose = readFileSync(join(repoRoot, 'docker-compose.prod.yml'), 'utf8');
const webService = prodCompose.slice(prodCompose.indexOf('\n  web:'), prodCompose.indexOf('\n  caddy:'));
const apiEnv = prodCompose.slice(prodCompose.indexOf('x-app-environment:'), prodCompose.indexOf('\n  web:'));
assert.match(webService, /NEXT_PUBLIC_API_URL:/);
assert.doesNotMatch(webService, /JWT_SECRET:/);
assert.match(webService, /AUTH_COOKIE_DOMAIN: "os\.investhome\.com"/);
assert.match(apiEnv, /JWT_SECRET:/);
assert.match(apiEnv, /AUTH_COOKIE_DOMAIN: "os\.investhome\.com"/);

const loginPage = readFileSync(join(webSrc, '../app/login/page.tsx'), 'utf8');
assert.match(loginPage, /import \{ safeInternalPath \} from '@\/lib\/auth\/session-cookie'/);
assert.match(loginPage, /redirectStartedRef/);
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

console.log('session-cookie auth gate checks passed');
