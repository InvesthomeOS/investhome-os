'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useLocale } from 'next-intl';

import { EmptyState } from '@investhome/ui';

import { CrmModuleShell } from '../../../_components/crm-module-shell';

export default function ContactJourneyPage() {
  const params = useParams<{ contactId: string }>();
  const locale = useLocale();
  const tr = !locale.startsWith('en');
  const contactId = params.contactId;
  return (
    <CrmModuleShell titleKey="modules.contacts.title" descriptionKey="modules.contacts.description">
      <EmptyState
        title={tr ? 'Yolculuk geçmişi burada yok' : 'Journey history is not available here'}
        description={
          tr
            ? 'Bu sayfa kişi geçmişi göstermez. Gerçek zaman çizelgesi kişi kartındadır.'
            : 'This page does not show a customer history. The contact card has the real timeline.'
        }
        action={
          <Link href={`/workspaces/crm/contacts/${contactId}` as Route}>
            {tr ? 'Kişi kartına dön' : 'Back to the contact card'}
          </Link>
        }
      />
    </CrmModuleShell>
  );
}
