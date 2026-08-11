import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

import {
  SESSION_COOKIE,
  isValidSessionJwt,
} from '@/lib/auth/session-cookie';

const PORTAL_SESSION_COOKIE = 'ih_portal_session';

function clearSessionCookie(response: NextResponse): void {
  response.cookies.set(SESSION_COOKIE, '', {
    path: '/',
    maxAge: 0,
    httpOnly: true,
    secure: process.env.AUTH_COOKIE_SECURE === 'true',
    sameSite: (process.env.AUTH_COOKIE_SAMESITE as 'lax' | 'strict' | 'none') || 'lax',
  });
}

function redirectToLogin(request: NextRequest, clearCookie: boolean): NextResponse {
  const loginUrl = new URL('/login', request.url);
  loginUrl.searchParams.set('next', request.nextUrl.pathname);
  const response = NextResponse.redirect(loginUrl);
  if (clearCookie) {
    clearSessionCookie(response);
  }
  return response;
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = request.cookies.get(SESSION_COOKIE)?.value;
  const portalSession = request.cookies.get(PORTAL_SESSION_COOKIE)?.value;

  // Public auth route: always reachable, even with a stale/bogus cookie.
  // Do not treat cookie presence as proof of authentication.
  if (pathname === '/login' || pathname.startsWith('/login/')) {
    return NextResponse.next();
  }

  if (
    pathname.startsWith('/dashboard') ||
    pathname.startsWith('/company') ||
    pathname.startsWith('/workspaces')
  ) {
    const valid = await isValidSessionJwt(session);
    if (!valid) {
      return redirectToLogin(request, Boolean(session));
    }
    return NextResponse.next();
  }

  if (pathname.startsWith('/portal')) {
    const isLogin = pathname === '/portal/login' || pathname.startsWith('/portal/login/');
    if (!portalSession && !isLogin) {
      const loginUrl = new URL('/portal/login', request.url);
      loginUrl.searchParams.set('next', pathname);
      return NextResponse.redirect(loginUrl);
    }
    if (portalSession && isLogin) {
      return NextResponse.redirect(new URL('/portal', request.url));
    }
    return NextResponse.next();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/company/:path*',
    '/workspaces/:path*',
    '/login',
    '/login/:path*',
    '/portal',
    '/portal/:path*',
  ],
};
