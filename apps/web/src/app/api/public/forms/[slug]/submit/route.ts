import { NextRequest, NextResponse } from 'next/server';

import { getApiBaseUrl } from '@/lib/api/client';

export const dynamic = 'force-dynamic';

const MAX_PUBLIC_FORM_BODY_BYTES = 32_768;

/**
 * Same-origin proxy for public marketing form submits.
 * Avoids browser CORS friction and keeps the public site talkative when the API is up.
 */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  const declaredLength = request.headers.get('content-length');
  if (declaredLength && Number(declaredLength) > MAX_PUBLIC_FORM_BODY_BYTES) {
    return NextResponse.json({ detail: 'Payload too large' }, { status: 413 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }

  let serialized: string;
  try {
    serialized = JSON.stringify(body);
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }
  if (serialized.length > MAX_PUBLIC_FORM_BODY_BYTES) {
    return NextResponse.json({ detail: 'Payload too large' }, { status: 413 });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  const forwarded = request.headers.get('x-forwarded-for');
  const realIp = request.headers.get('x-real-ip');

  try {
    const upstreamHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
    if (forwarded) upstreamHeaders['X-Forwarded-For'] = forwarded;
    if (realIp) upstreamHeaders['X-Real-IP'] = realIp;

    const upstream = await fetch(
      `${getApiBaseUrl()}/public/marketing/forms/${encodeURIComponent(slug)}/submit`,
      {
        method: 'POST',
        headers: upstreamHeaders,
        body: serialized,
        signal: controller.signal,
        cache: 'no-store',
      },
    );

    const text = await upstream.text();
    let json: unknown = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {
      json = { detail: text || 'Upstream error' };
    }

    const retryAfter = upstream.headers.get('retry-after');
    return NextResponse.json(json, {
      status: upstream.status,
      headers: retryAfter ? { 'Retry-After': retryAfter } : undefined,
    });
  } catch (err) {
    const aborted =
      (err instanceof DOMException && err.name === 'AbortError') ||
      (err instanceof Error && /abort/i.test(err.message));
    return NextResponse.json(
      {
        detail: aborted ? 'Upstream timeout' : 'Upstream unreachable',
        code: aborted ? 'timeout' : 'upstream_unreachable',
      },
      { status: aborted ? 504 : 502 },
    );
  } finally {
    clearTimeout(timer);
  }
}
