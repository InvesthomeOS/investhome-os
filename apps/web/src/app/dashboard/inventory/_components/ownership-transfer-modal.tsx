'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { TransferRequestInput, OwnershipRecord } from '@/lib/api/inventory-ownership';
import type { InventoryAsset } from '@/lib/api/inventory';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

interface OwnershipTransferModalProps {
  asset: InventoryAsset;
  currentLegal: OwnershipRecord[];
  onClose: () => void;
  onSubmit: (input: TransferRequestInput) => Promise<void>;
}

export function OwnershipTransferModal({
  asset,
  currentLegal,
  onClose,
  onSubmit,
}: OwnershipTransferModalProps) {
  const t = useTranslations('inventory.ownership');
  const { getTransferTypeLabel } = useInventoryLabels();
  const today = new Date().toISOString().slice(0, 10);

  const isInitial = currentLegal.length === 0;
  const [transferType, setTransferType] = useState<'initial_ownership' | 'partial_transfer' | 'percentage_change'>(
    isInitial ? 'initial_ownership' : 'partial_transfer',
  );
  const [effectiveDate, setEffectiveDate] = useState(today);
  const [reason, setReason] = useState('');
  const [partyId, setPartyId] = useState('');
  const [secondPartyId, setSecondPartyId] = useState('');
  const [firstPct, setFirstPct] = useState(isInitial ? '100' : '50');
  const [secondPct, setSecondPct] = useState('50');
  const [documentId, setDocumentId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const proposedTotal = useMemo(() => {
    if (isInitial) return Number.parseFloat(firstPct) || 0;
    return (Number.parseFloat(firstPct) || 0) + (Number.parseFloat(secondPct) || 0);
  }, [firstPct, secondPct, isInitial]);

  const valid = proposedTotal === 100 && reason.trim().length > 0 && partyId.trim().length > 0;

  const handleSubmit = async () => {
    if (!valid) return;
    setBusy(true);
    setError(null);
    try {
      const parties = isInitial
        ? [
            {
              party_id: partyId,
              ownership_type: 'legal_owner' as const,
              proposed_percentage: firstPct,
              role: 'incoming_owner' as const,
            },
          ]
        : [
            {
              party_id: partyId,
              ownership_type: 'legal_owner' as const,
              previous_percentage: currentLegal[0]?.ownership_percentage ?? null,
              proposed_percentage: firstPct,
              role: 'continuing_owner' as const,
            },
            {
              party_id: secondPartyId,
              ownership_type: 'legal_owner' as const,
              proposed_percentage: secondPct,
              role: 'incoming_owner' as const,
            },
          ];

      await onSubmit({
        inventory_asset_id: asset.id,
        transfer_type: transferType,
        effective_date: effectiveDate,
        reason: reason.trim(),
        parties,
        supporting_document_id: documentId.trim() || null,
        submit: true,
      });
    } catch {
      setError(t('actionError'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="leads-modal" role="dialog" aria-modal="true">
      <div className="leads-modal__panel">
        <header className="leads-modal__header">
          <h2>{t('transferFormTitle')}</h2>
          <button type="button" className="leads-modal__close" onClick={onClose} aria-label={t('close')}>
            ×
          </button>
        </header>
        <div className="leads-modal__body">
          {error && <p className="leads__state leads__state--error">{error}</p>}

          <label>
            <span>{t('fields.transferType')}</span>
            <select value={transferType} onChange={(e) => setTransferType(e.target.value as typeof transferType)}>
              {isInitial ? (
                <option value="initial_ownership">{getTransferTypeLabel('initial_ownership')}</option>
              ) : (
                <>
                  <option value="partial_transfer">{getTransferTypeLabel('partial_transfer')}</option>
                  <option value="percentage_change">{getTransferTypeLabel('percentage_change')}</option>
                </>
              )}
            </select>
          </label>

          <label>
            <span>{t('fields.effectiveDate')}</span>
            <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
          </label>

          <label>
            <span>{t('fields.partyId')}</span>
            <input value={partyId} onChange={(e) => setPartyId(e.target.value)} placeholder={t('fields.partyIdHint')} />
          </label>

          {!isInitial && (
            <>
              <label>
                <span>{t('fields.continuingPercentage')}</span>
                <input type="number" min="0.0001" max="100" step="0.01" value={firstPct} onChange={(e) => setFirstPct(e.target.value)} />
              </label>
              <label>
                <span>{t('fields.incomingPartyId')}</span>
                <input value={secondPartyId} onChange={(e) => setSecondPartyId(e.target.value)} />
              </label>
              <label>
                <span>{t('fields.incomingPercentage')}</span>
                <input type="number" min="0.0001" max="100" step="0.01" value={secondPct} onChange={(e) => setSecondPct(e.target.value)} />
              </label>
            </>
          )}

          {isInitial && (
            <label>
              <span>{t('fields.percentage')}</span>
              <input type="number" min="0.0001" max="100" step="0.01" value={firstPct} onChange={(e) => setFirstPct(e.target.value)} />
            </label>
          )}

          <label>
            <span>{t('fields.supportingDocument')}</span>
            <input value={documentId} onChange={(e) => setDocumentId(e.target.value)} placeholder={t('fields.documentOptional')} />
          </label>

          <label>
            <span>{t('fields.reason')}</span>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
          </label>

          <p className={proposedTotal === 100 ? 'leads__state' : 'leads__state leads__state--error'}>
            {t('proposedTotal')}: {proposedTotal.toFixed(2)}%
          </p>
        </div>
        <footer className="leads-modal__footer">
          <Button variant="secondary" onClick={onClose}>
            {t('cancel')}
          </Button>
          <Button variant="primary" disabled={!valid || busy} onClick={() => void handleSubmit()}>
            {t('submitTransfer')}
          </Button>
        </footer>
      </div>
    </div>
  );
}
