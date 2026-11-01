'use client';

import { useTranslations } from 'next-intl';

import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { uiError } from '@/lib/i18n/ui-error';
import { fetchPurchaseCard } from '@/workspaces/crm/api/agreements';
import { PurchaseDetailView } from '@/workspaces/crm/contact-card/purchase-detail-view';

export function SalesDetailPage({ contactId, agreementId }: { contactId: string; agreementId: string }) {
  const tCommon = useTranslations('common');
  const tCard = useTranslations('crm.contactCard.ui');
  const router = useRouter();
  const query = useQuery({
    queryKey: ['crm', 'sales-detail', agreementId, contactId],
    queryFn: () => fetchPurchaseCard(agreementId, contactId, { includeHidden: true }),
    enabled: Boolean(agreementId),
  });

  if (query.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (query.isError || !query.data) {
    return <ErrorState title={tCard('k394c0f77c0')} message={uiError(query.error, tCommon('loadFailed'))} />;
  }

  return (
    <main className="dashboard crm-module-shell crm-sales-page">
      <PurchaseDetailView
        card={query.data}
        contactId={contactId}
        onOpenContact={(id) => router.push(`/workspaces/crm/contacts/${id}`)}
        onBack={() => router.push(`/workspaces/crm/contacts/${contactId}`)}
        onRefresh={() => {
          void query.refetch();
        }}
      />
    </main>
  );
}
