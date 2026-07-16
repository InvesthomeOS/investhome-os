'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { AssignmentRequestInput } from '@/lib/api/inventory-assignment';
import { isParkingAsset, isStorageAsset, type InventoryAsset } from '@/lib/api/inventory';

interface AssignmentFormModalProps {
  asset: InventoryAsset;
  parentUnits: InventoryAsset[];
  currentParentId: string | null;
  onClose: () => void;
  onSubmit: (input: AssignmentRequestInput) => Promise<void>;
}

export function AssignmentFormModal({
  asset,
  parentUnits,
  currentParentId,
  onClose,
  onSubmit,
}: AssignmentFormModalProps) {
  const t = useTranslations('inventory.assignments');
  const today = new Date().toISOString().slice(0, 10);
  const isChild = isParkingAsset(asset.asset_type) || isStorageAsset(asset.asset_type);

  const [mode, setMode] = useState<'assign' | 'unassign'>(currentParentId ? 'assign' : 'assign');
  const [parentId, setParentId] = useState(currentParentId ?? parentUnits[0]?.id ?? '');
  const [effectiveDate, setEffectiveDate] = useState(today);
  const [reason, setReason] = useState('');
  const [price, setPrice] = useState('');
  const [currency, setCurrency] = useState(asset.currency || 'USD');
  const [documentId, setDocumentId] = useState('');
  const [transactionId, setTransactionId] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valid =
    reason.trim().length > 0 &&
    (mode === 'unassign' || parentId.trim().length > 0) &&
    isChild;

  const handleSubmit = async () => {
    if (!valid) return;
    setBusy(true);
    setError(null);
    try {
      await onSubmit({
        child_asset_id: asset.id,
        parent_asset_id: mode === 'unassign' ? null : parentId,
        request_type: mode === 'unassign' ? 'unassign' : undefined,
        effective_date: effectiveDate,
        reason: reason.trim(),
        assignment_price: price.trim() || null,
        currency,
        supporting_document_id: documentId.trim() || null,
        related_transaction_id: transactionId.trim() || null,
        submit: true,
      });
    } catch {
      setError(t('formError'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="leads-modal" role="dialog" aria-modal="true">
      <div className="leads-modal__panel">
        <header className="leads-modal__header">
          <h2>{t('formTitle')}</h2>
          <button type="button" className="leads-modal__close" onClick={onClose} aria-label={t('close')}>
            ×
          </button>
        </header>
        <div className="leads-modal__body">
          {error && <p className="leads__state leads__state--error">{error}</p>}

          {currentParentId && (
            <label>
              <span>{t('fields.action')}</span>
              <select value={mode} onChange={(e) => setMode(e.target.value as 'assign' | 'unassign')}>
                <option value="assign">{t('reassign')}</option>
                <option value="unassign">{t('unassign')}</option>
              </select>
            </label>
          )}

          {mode !== 'unassign' && (
            <label>
              <span>{t('fields.parentUnit')}</span>
              <select value={parentId} onChange={(e) => setParentId(e.target.value)}>
                {parentUnits.map((unit) => (
                  <option key={unit.id} value={unit.id}>
                    {unit.display_id} ({unit.system_code})
                  </option>
                ))}
              </select>
            </label>
          )}

          <label>
            <span>{t('fields.effectiveDate')}</span>
            <input type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
          </label>

          <label>
            <span>{t('fields.reason')}</span>
            <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
          </label>

          {mode !== 'unassign' && (
            <>
              <label>
                <span>{t('fields.assignmentPrice')}</span>
                <input type="text" inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} />
              </label>
              <label>
                <span>{t('fields.currency')}</span>
                <input type="text" maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
              </label>
            </>
          )}

          <label>
            <span>{t('fields.supportingDocumentId')}</span>
            <input type="text" value={documentId} onChange={(e) => setDocumentId(e.target.value)} />
          </label>

          <label>
            <span>{t('fields.relatedTransactionId')}</span>
            <input type="text" value={transactionId} onChange={(e) => setTransactionId(e.target.value)} />
          </label>
        </div>
        <footer className="leads-modal__footer">
          <Button variant="secondary" onClick={onClose}>
            {t('cancel')}
          </Button>
          <Button disabled={!valid || busy} onClick={() => void handleSubmit()}>
            {t('submitRequest')}
          </Button>
        </footer>
      </div>
    </div>
  );
}
