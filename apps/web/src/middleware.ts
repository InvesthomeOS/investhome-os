import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

import {
  SESSION_COOKIE,
  authorizeStaffSession,
  clearedSessionCookieOptions,
} from '@/lib/auth/session-cookie';
import {
  PORTAL_SESSION_COOKIE,
  isValidPortalSession,
  portalAccessDecision,
  safePortalPath,
} from '@/lib/auth/portal-session-cookie';
import { LOCALE_COOKIE } from '@/i18n/config';
import { authServiceUnavailableMessage } from '@/lib/i18n/auth-unavailable';
import { applySecurityHeaders, createCspNonce } from '@/lib/security/security-headers';

function withSecurity(request: NextRequest, response: NextResponse, nonce: string): NextResponse {
  applySecurityHeaders(response.headers, {
    nonce,
    protocol: request.nextUrl.protocol,
    forwardedProto: request.headers.get('x-forwarded-proto'),
    cookieSecure: process.env.AUTH_COOKIE_SECURE === 'true',
    isDev: process.env.NODE_ENV !== 'production',
    apiUrl: process.env.NEXT_PUBLIC_API_URL,
  });
  return response;
}

function continueRequest(request: NextRequest): NextResponse {
  const nonce = createCspNonce();
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);
  const response = NextResponse.next({
    request: { headers: requestHeaders },
  });
  return withSecurity(request, response, nonce);
}

function cookieClearOptions() {
  return {
    path: '/',
    maxAge: 0,
    httpOnly: true,
    secure: process.env.AUTH_COOKIE_SECURE === 'true',
    sameSite: (process.env.AUTH_COOKIE_SAMESITE as 'lax' | 'strict' | 'none') || 'lax',
  };
}

function clearSessionCookie(response: NextResponse): void {
  const cleared = clearedSessionCookieOptions();
  const sameSite =
    cleared.sameSite === 'strict' || cleared.sameSite === 'none' ? cleared.sameSite : 'lax';
  response.cookies.set(SESSION_COOKIE, '', {
    path: '/',
    maxAge: 0,
    httpOnly: true,
    secure: cleared.secure === true,
    sameSite,
    ...(typeof cleared.domain === 'string' && cleared.domain ? { domain: cleared.domain } : {}),
  });
}

function clearPortalSessionCookie(response: NextResponse): void {
  response.cookies.set(PORTAL_SESSION_COOKIE, '', cookieClearOptions());
}

function authUnavailable(request: NextRequest): NextResponse {
  const nonce = createCspNonce();
  const response = new NextResponse(authServiceUnavailableMessage(request.cookies.get(LOCALE_COOKIE)?.value), {
    status: 503,
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
  return withSecurity(request, response, nonce);
}

function redirectToLogin(request: NextRequest, clearCookie: boolean): NextResponse {
  const loginUrl = new URL('/login', request.url);
  loginUrl.searchParams.set('next', request.nextUrl.pathname);
  const nonce = createCspNonce();
  const response = NextResponse.redirect(loginUrl);
  if (clearCookie) {
    clearSessionCookie(response);
  }
  return withSecurity(request, response, nonce);
}

function redirectToPortalLogin(request: NextRequest, clearCookie: boolean): NextResponse {
  const loginUrl = new URL('/portal/login', request.url);
  loginUrl.searchParams.set('next', safePortalPath(request.nextUrl.pathname));
  const nonce = createCspNonce();
  const response = NextResponse.redirect(loginUrl);
  if (clearCookie) {
    clearPortalSessionCookie(response);
  }
  return withSecurity(request, response, nonce);
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = request.cookies.get(SESSION_COOKIE)?.value;
  const portalSession = request.cookies.get(PORTAL_SESSION_COOKIE)?.value;

  // Public auth route: always reachable, even with a stale/bogus cookie.
  // Do not treat cookie presence as proof of authentication.
  if (pathname === '/login' || pathname.startsWith('/login/') || pathname.startsWith('/invite')) {
    return continueRequest(request);
  }

  if (
    pathname.startsWith('/dashboard') ||
    pathname.startsWith('/company') ||
    pathname.startsWith('/workspaces')
  ) {
    const decision = await authorizeStaffSession(session);
    if (decision.allow) return continueRequest(request);
    if (decision.unavailable) return authUnavailable(request);
    return redirectToLogin(request, decision.clearCookie);
  }

  if (pathname === '/portal' || pathname.startsWith('/portal/')) {
    const portalValid = await isValidPortalSession(portalSession);
    const decision = portalAccessDecision(pathname, portalValid);
    if (decision === 'redirect-login') {
      return redirectToPortalLogin(request, Boolean(portalSession));
    }
    if (decision === 'redirect-home') {
      const nonce = createCspNonce();
      return withSecurity(request, NextResponse.redirect(new URL('/portal', request.url)), nonce);
    }
    return continueRequest(request);
  }

  return continueRequest(request);
}

export const config = {
  matcher: [
    {
      source:
        '/((?!_next/static|_next/image|_next/webpack-hmr|favicon.ico|brand/|.*\\.(?:ico|png|jpg|jpeg|gif|webp|svg|woff2)$).*)',
    },
  ],
};
