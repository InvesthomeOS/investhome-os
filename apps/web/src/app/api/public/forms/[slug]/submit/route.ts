import { NextRequest, NextResponse } from 'next/server';

import { getApiBaseUrl } from '@/lib/api/client';

export const dynamic = 'force-dynamic';

/**
 * Same-origin proxy for public marketing form submits.
 * Avoids browser CORS friction and keeps the public site talkative when the API is up.
 */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ slug: string }> },
) {
  const { slug } = await context.params;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: 'Invalid JSON body' }, { status: 400 });
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);

  try {
    const upstream = await fetch(
      `${getApiBaseUrl()}/public/marketing/forms/${encodeURIComponent(slug)}/submit`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
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

    return NextResponse.json(json, { status: upstream.status });
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
