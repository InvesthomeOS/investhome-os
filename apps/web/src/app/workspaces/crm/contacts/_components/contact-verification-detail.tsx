'use client';

import { useParams, usePathname } from 'next/navigation';

import { UnifiedContactCard } from '@/workspaces/crm/contact-card/unified-contact-card';

function personIdFromRoute(pathname: string | null, paramId: string | undefined, fallback: string): string {
  const fromPath = pathname?.match(/\/contacts\/([0-9a-fA-F-]{36})(?:\/|$)/)?.[1];
  if (fromPath) return fromPath;
  if (typeof paramId === 'string' && paramId) return paramId;
  return fallback;
}

export function ContactVerificationDetail({ contactId }: { contactId: string }) {
  const pathname = usePathname();
  const params = useParams<{ contactId?: string }>();
  const id = personIdFromRoute(pathname, params.contactId, contactId);
  return <UnifiedContactCard key={id} contactId={id} />;
}
