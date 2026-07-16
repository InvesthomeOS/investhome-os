'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog } from '@investhome/ui';

import { computeChangePreview, PRICE_TYPES, type PriceType } from '@/lib/api/inventory-pricing';
import type { InventoryAsset } from '@/lib/api/inventory';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

interface PriceChangeModalProps {
  asset: InventoryAsset;
  initialMode: boolean;
  currentListPrice: number | null;
  onClose: () => void;
  onSubmitInitial: (input: {
    price_type: PriceType;
    amount: number;
    effective_from: string;
    reason: string;
  }) => Promise<void>;
  onSubmitChange: (input: {
    price_type: PriceType;
    proposed_amount: number;
    effective_from: string;
    effective_to?: string | null;
    reason: string;
    submit: boolean;
  }) => Promise<void>;
}

export function PriceChangeModal({
  asset,
  initialMode,
  currentListPrice,
  onClose,
  onSubmitInitial,
  onSubmitChange,
}: PriceChangeModalProps) {
  const t = useTranslations('inventory.pricing.form');
  const { getPriceTypeLabel } = useInventoryLabels();
  const today = new Date().toISOString().slice(0, 10);

  const [priceType, setPriceType] = useState<PriceType>(initialMode ? 'list' : 'list');
  const [amount, setAmount] = useState('');
  const [effectiveFrom, setEffectiveFrom] = useState(today);
  const [effectiveTo, setEffectiveTo] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const proposed = Number(amount);
  const preview = useMemo(() => {
    if (!amount || Number.isNaN(proposed)) return null;
    return computeChangePreview(currentListPrice, proposed);
  }, [amount, currentListPrice, proposed]);

  const showLargeWarning =
    preview?.changePercent !== null &&
    preview?.changePercent !== undefined &&
    Math.abs(preview.changePercent) >= 10;

  const handleSubmit = async (submit: boolean) => {
    if (!reason.trim() || !amount || Number.isNaN(proposed) || proposed <= 0) return;
    setSubmitting(true);
    try {
      if (initialMode) {
        await onSubmitInitial({
          price_type: priceType,
          amount: proposed,
          effective_from: effectiveFrom,
          reason: reason.trim(),
        });
      } else {
        await onSubmitChange({
          price_type: priceType,
          proposed_amount: proposed,
          effective_from: effectiveFrom,
          effective_to: effectiveTo || null,
          reason: reason.trim(),
          submit,
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      title={initialMode ? t('initialTitle') : t('changeTitle')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            {t('cancel')}
          </Button>
          {!initialMode && (
            <Button variant="secondary" disabled={submitting} onClick={() => void handleSubmit(false)}>
              {t('saveDraft')}
            </Button>
          )}
          <Button variant="primary" disabled={submitting} onClick={() => void handleSubmit(true)}>
            {initialMode ? t('create') : t('submit')}
          </Button>
        </>
      }
    >
      <div className="inventory__price-form">
        <label>
          {t('priceType')}
          <select
            className="leads__select"
            value={priceType}
            onChange={(event) => setPriceType(event.target.value as PriceType)}
            disabled={initialMode}
          >
            {PRICE_TYPES.map((type) => (
              <option key={type} value={type}>
                {getPriceTypeLabel(type)}
              </option>
            ))}
          </select>
        </label>

        {!initialMode && (
          <p className="leads__meta">
            {t('currentPrice')}: {currentListPrice ?? '—'} {asset.currency}
          </p>
        )}

        <label>
          {initialMode ? t('amount') : t('proposedPrice')}
          <input
            className="leads__input"
            type="number"
            min={0}
            step="0.01"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
          />
        </label>

        <label>
          {t('currency')}
          <input className="leads__input" value={asset.currency} readOnly />
        </label>

        <label>
          {t('effectiveFrom')}
          <input
            className="leads__input"
            type="date"
            value={effectiveFrom}
            onChange={(event) => setEffectiveFrom(event.target.value)}
          />
        </label>

        {!initialMode && (
          <label>
            {t('effectiveTo')}
            <input
              className="leads__input"
              type="date"
              value={effectiveTo}
              onChange={(event) => setEffectiveTo(event.target.value)}
            />
          </label>
        )}

        <label>
          {t('reason')}
          <textarea
            className="leads__input"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>

        {preview && !initialMode && (
          <div className="inventory__price-preview">
            <p>
              {t('changeAmount')}: {preview.changeAmount.toFixed(2)} {asset.currency}
            </p>
            {preview.changePercent !== null && (
              <p>
                {t('changePercent')}: {preview.changePercent.toFixed(2)}%
              </p>
            )}
            {showLargeWarning && <p className="inventory__pricing-warning">{t('largeChangeWarning')}</p>}
          </div>
        )}
      </div>
    </Dialog>
  );
}
