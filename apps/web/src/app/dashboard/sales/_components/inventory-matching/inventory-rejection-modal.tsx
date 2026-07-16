'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { MatchRejectionReason } from '@/lib/api/sales-inventory-matching';
import { useSalesInventoryMatchingLabels } from '@/lib/i18n/sales-inventory-matching-labels';

interface InventoryRejectionModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: MatchRejectionReason, notes?: string) => Promise<void>;
}

export function InventoryRejectionModal({ open, onClose, onConfirm }: InventoryRejectionModalProps) {
  const t = useTranslations('salesInventoryMatching');
  const { rejectionReasonOptions } = useSalesInventoryMatchingLabels();
  const [reason, setReason] = useState<MatchRejectionReason>('budget');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-card">
        <h3>{t('reject.title')}</h3>
        <label className="leads__field">
          <span>{t('reject.reason')}</span>
          <select value={reason} onChange={(e) => setReason(e.target.value as MatchRejectionReason)}>
            {rejectionReasonOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </label>
        <label className="leads__field">
          <span>{t('reject.notes')}</span>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
        </label>
        <div className="modal-card__actions">
          <Button variant="ghost" onClick={onClose}>{t('actions.cancel')}</Button>
          <Button
            disabled={submitting}
            onClick={() => {
              setSubmitting(true);
              void onConfirm(reason, notes || undefined).finally(() => {
                setSubmitting(false);
                onClose();
              });
            }}
          >
            {t('actions.confirmReject')}
          </Button>
        </div>
      </div>
    </div>
  );
}
