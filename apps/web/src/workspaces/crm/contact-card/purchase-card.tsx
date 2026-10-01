'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { fetchPurchaseCard } from '@/workspaces/crm/api/agreements';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { PurchaseDetailView } from '@/workspaces/crm/contact-card/purchase-detail-view';

export function PurchaseCard({ agreementId }: { agreementId: string }) {
  const { openContact, closePurchase } = useContactCard();
  const router = useRouter();
  const pathname = usePathname();
  const fromContactId = pathname?.match(/\/contacts\/([0-9a-fA-F-]{36})/)?.[1] || null;
  const query = useQuery({
    queryKey: ['crm', 'purchases', agreementId, fromContactId],
    queryFn: () => fetchPurchaseCard(agreementId, fromContactId),
    enabled: Boolean(agreementId),
  });

  if (query.isLoading) return <LoadingState label="Loading…" />;
  if (query.isError || !query.data) {
    return <ErrorState title="Satın alma" message={query.error?.message ?? 'Purchase unavailable'} />;
  }

  const card = query.data;
  const viewer = card.participants.find((item) => item.contact_id === fromContactId)
    || card.participants.find((item) => item.is_primary)
    || card.participants[0];

  return (
    <div className="crm-contact-card crm-purchase-card" data-testid="purchase-card">
      <PurchaseDetailView
        card={card}
        contactId={fromContactId || viewer?.contact_id || card.primary_contact_id}
        pageTestId="purchase-card-detail"
        onOpenContact={openContact}
        onBack={() => {
          if (fromContactId) {
            closePurchase();
            return;
          }
          if (viewer?.contact_id) {
            router.push(`/workspaces/crm/contacts/${viewer.contact_id}`);
            return;
          }
          closePurchase();
        }}
        onRefresh={() => {
          void query.refetch();
        }}
      />
    </div>
  );
}
