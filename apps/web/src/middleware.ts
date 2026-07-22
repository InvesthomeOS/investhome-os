import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const SESSION_COOKIE = 'ih_session';
const PORTAL_SESSION_COOKIE = 'ih_portal_session';

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const session = request.cookies.get(SESSION_COOKIE)?.value;
  const portalSession = request.cookies.get(PORTAL_SESSION_COOKIE)?.value;

  if (
    pathname.startsWith('/dashboard') ||
    pathname.startsWith('/company') ||
    pathname.startsWith('/workspaces')
  ) {
    if (!session) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('next', pathname);
      return NextResponse.redirect(loginUrl);
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

  if (pathname === '/login' && session) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/company/:path*',
    '/workspaces/:path*',
    '/login',
    '/portal',
    '/portal/:path*',
  ],
};
