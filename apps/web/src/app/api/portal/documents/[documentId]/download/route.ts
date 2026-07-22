import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

import { canDownloadDocument, getDocumentFor } from '@/app/portal/_lib/permissions';
import { PORTAL_SESSION_COOKIE, decodePortalSession } from '@/app/portal/_lib/session';

type RouteContext = { params: Promise<{ documentId: string }> };

/**
 * Permission-checked portal document download.
 * Returns 403 when the session investor does not own the document.
 */
export async function GET(_request: Request, context: RouteContext) {
  const { documentId } = await context.params;
  const jar = await cookies();
  const session = decodePortalSession(jar.get(PORTAL_SESSION_COOKIE)?.value);
  if (!session) {
    return NextResponse.json({ error: 'unauthenticated' }, { status: 401 });
  }

  if (!canDownloadDocument(session.investorId, documentId)) {
    return NextResponse.json(
      {
        error: 'forbidden',
        message: 'Document not available for this investor session',
        documentId,
        investorId: session.investorId,
      },
      { status: 403 },
    );
  }

  const doc = getDocumentFor(session.investorId, documentId);
  if (!doc) {
    return NextResponse.json({ error: 'not_found' }, { status: 404 });
  }

  const body = [
    'INVESTHOME OS — Investor Portal Document',
    `Title: ${doc.title}`,
    `Version: ${doc.version}`,
    `Investor: ${session.investorId}`,
    `Category: ${doc.category}`,
    '',
    'This is a permission-scoped demo payload.',
    'Cross-investor access is denied by the download gate.',
  ].join('\n');

  return new NextResponse(body, {
    status: 200,
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Content-Disposition': `attachment; filename="${doc.id}-${doc.version}.txt"`,
      'X-Portal-Document-Id': doc.id,
      'X-Portal-Investor-Id': session.investorId,
      'Cache-Control': 'no-store',
    },
  });
}
