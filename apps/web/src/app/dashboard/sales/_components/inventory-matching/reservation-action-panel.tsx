'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

interface ReservationActionPanelProps {
  leadId?: string;
  opportunityId?: string;
  selectedAssetId?: string;
  onSoftHold: (body: {
    inventory_asset_id: string;
    lead_id?: string;
    opportunity_id?: string;
    notes?: string;
  }) => Promise<Record<string, unknown>>;
  onComplete: () => Promise<void>;
}

export function ReservationActionPanel({
  leadId,
  opportunityId,
  selectedAssetId,
  onSoftHold,
  onComplete,
}: ReservationActionPanelProps) {
  const t = useTranslations('salesInventoryMatching');
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!selectedAssetId) {
    return <p className="sales-muted">{t('reservation.selectAsset')}</p>;
  }

  return (
    <div className="reservation-action-panel">
      <p>{t('reservation.selectedAsset', { id: selectedAssetId.slice(0, 8) })}</p>
      <label className="leads__field">
        <span>{t('reservation.notes')}</span>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
      </label>
      <Button
        disabled={submitting}
        onClick={() => {
          setSubmitting(true);
          void onSoftHold({
            inventory_asset_id: selectedAssetId,
            lead_id: leadId,
            opportunity_id: opportunityId,
            notes: notes || undefined,
          })
            .then((res) => {
              setMessage(t('reservation.softHoldCreated', { id: String(res.id ?? '').slice(0, 8) }));
              return onComplete();
            })
            .catch(() => setMessage(t('reservation.error')))
            .finally(() => setSubmitting(false));
        }}
      >
        {t('actions.placeSoftHold')}
      </Button>
      {message && <p className="sales-muted">{message}</p>}
      <p className="sales-muted">{t('reservation.inventoryNote')}</p>
    </div>
  );
}
