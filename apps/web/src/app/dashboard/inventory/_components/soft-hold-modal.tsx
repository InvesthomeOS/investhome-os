'use client';

import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Dialog, Select } from '@investhome/ui';

import { createSoftHold, formatDateTime, type InventoryAsset } from '@/lib/api/inventory';
import { fetchInvestors, type Investor } from '@/lib/api/investors';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

interface SoftHoldModalProps {
  asset: InventoryAsset | null;
  open: boolean;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmittingChange: (value: boolean) => void;
  onError: (message: string | null) => void;
  onSuccess: () => void;
}

export function SoftHoldModal({
  asset,
  open,
  submitting,
  error,
  onClose,
  onSubmittingChange,
  onError,
  onSuccess,
}: SoftHoldModalProps) {
  const t = useTranslations('inventory.reservation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getReservationRecordLabel } = useInventoryLabels();
  const [investors, setInvestors] = useState<Investor[]>([]);
  const [investorId, setInvestorId] = useState('');
  const [notes, setNotes] = useState('');
  const [depositAmount, setDepositAmount] = useState('');

  useEffect(() => {
    if (!open) return;
    void fetchInvestors({ page_size: 100 }).then((response) => setInvestors(response.items)).catch(() => setInvestors([]));
    setInvestorId('');
    setNotes('');
    setDepositAmount('');
    onError(null);
  }, [open, onError]);

  if (!open || !asset) return null;

  const defaultExpiry = new Date(Date.now() + 48 * 60 * 60 * 1000);

  const handleSubmit = async () => {
    if (!investorId) {
      onError(t('partyRequired'));
      return;
    }
    onSubmittingChange(true);
    onError(null);
    try {
      await createSoftHold({
        inventory_asset_id: asset.id,
        investor_id: investorId,
        notes: notes || null,
        deposit_amount: depositAmount ? Number(depositAmount) : null,
        deposit_currency: asset.currency,
      });
      onSuccess();
      onClose();
    } catch {
      onError(t('createError'));
    } finally {
      onSubmittingChange(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} title={t('softHoldTitle')} ariaLabel={t('softHoldTitle')}>
      <p className="leads__meta">{asset.display_id} · {asset.system_code}</p>
      <p className="leads__meta">{t('softHoldExpiryHint', { expiry: formatDateTime(defaultExpiry.toISOString(), locale) })}</p>

      <label className="leads__field">
        <span>{t('partyLabel')}</span>
        <Select value={investorId} onChange={(event) => setInvestorId(event.target.value)}>
          <option value="">{t('partyPlaceholder')}</option>
          {investors.map((investor) => (
            <option key={investor.id} value={investor.id}>
              {investor.full_name}
            </option>
          ))}
        </Select>
      </label>

      <label className="leads__field">
        <span>{t('depositAmount')}</span>
        <input
          type="number"
          min="0"
          step="0.01"
          value={depositAmount}
          onChange={(event) => setDepositAmount(event.target.value)}
          placeholder={t('depositOptional')}
        />
      </label>

      <label className="leads__field">
        <span>{t('notes')}</span>
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
      </label>

      <p className="leads__meta">{getReservationRecordLabel('active')}</p>

      {error && <p className="leads__state leads__state--error">{error}</p>}

      <div className="leads__modal-actions">
        <Button variant="secondary" onClick={onClose} disabled={submitting}>
          {tCommon('cancel')}
        </Button>
        <Button variant="primary" onClick={() => void handleSubmit()} disabled={submitting}>
          {submitting ? tCommon('saving') : t('placeSoftHold')}
        </Button>
      </div>
    </Dialog>
  );
}
