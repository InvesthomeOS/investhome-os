'use client';

import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { fetchPurchaseCard } from '@/workspaces/crm/api/agreements';
import { PurchaseDetailView } from '@/workspaces/crm/contact-card/purchase-detail-view';

export function SalesDetailPage({ contactId, agreementId }: { contactId: string; agreementId: string }) {
  const router = useRouter();
  const query = useQuery({
    queryKey: ['crm', 'sales-detail', agreementId, contactId],
    queryFn: () => fetchPurchaseCard(agreementId, contactId, { includeHidden: true }),
    enabled: Boolean(agreementId),
  });

  if (query.isLoading) return <LoadingState label="Yükleniyor…" />;
  if (query.isError || !query.data) {
    return <ErrorState title="Satın Alma Detayı" message={query.error?.message ?? 'Kayıt bulunamadı'} />;
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
