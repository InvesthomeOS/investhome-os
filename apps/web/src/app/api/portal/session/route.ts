import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { getInvestorProfile } from '@/app/portal/_lib/permissions';
import {
  PORTAL_SESSION_COOKIE,
  authenticatePortalDemo,
  decodePortalSession,
  encodePortalSession,
} from '@/app/portal/_lib/session';

export async function GET() {
  const jar = await cookies();
  const session = decodePortalSession(jar.get(PORTAL_SESSION_COOKIE)?.value);
  if (!session) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
  const profile = getInvestorProfile(session.investorId);
  if (!profile) {
    return NextResponse.json({ authenticated: false }, { status: 401 });
  }
  return NextResponse.json({
    authenticated: true,
    investorId: session.investorId,
    email: session.email,
    profile: {
      id: profile.id,
      fullName: profile.fullName,
      email: profile.email,
      avatarInitials: profile.avatarInitials,
      tier: profile.tier,
      twoFactorEnabled: profile.twoFactorEnabled,
    },
  });
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as {
    email?: string;
    password?: string;
  } | null;
  if (!body?.email || !body?.password) {
    return NextResponse.json({ error: 'missing_credentials' }, { status: 400 });
  }
  const session = authenticatePortalDemo(body.email, body.password);
  if (!session) {
    return NextResponse.json({ error: 'invalid_credentials' }, { status: 401 });
  }
  try {
    const jar = await cookies();
    jar.set(PORTAL_SESSION_COOKIE, encodePortalSession(session), {
      httpOnly: true,
      sameSite: 'lax',
      path: '/',
      secure: process.env.NODE_ENV === 'production',
      maxAge: 60 * 60 * 12,
    });
  } catch (err) {
    return NextResponse.json(
      {
        error: 'session_config',
        message: err instanceof Error ? err.message : 'Unable to issue portal session',
      },
      { status: 500 },
    );
  }
  const profile = getInvestorProfile(session.investorId);
  return NextResponse.json({
    authenticated: true,
    investorId: session.investorId,
    email: session.email,
    profile,
  });
}

export async function DELETE() {
  const jar = await cookies();
  jar.set(PORTAL_SESSION_COOKIE, '', {
    httpOnly: true,
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
  return NextResponse.json({ ok: true });
}
