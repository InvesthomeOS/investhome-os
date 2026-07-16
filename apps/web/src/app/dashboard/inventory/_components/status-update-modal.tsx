'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog, Select } from '@investhome/ui';

import {
  STATUS_CATEGORIES,
  type InventoryAsset,
  type StatusCategory,
  type StatusUpdateInput,
} from '@/lib/api/inventory';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

interface StatusUpdateModalProps {
  asset: InventoryAsset | null;
  open: boolean;
  submitting: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: StatusUpdateInput) => void;
}

export function StatusUpdateModal({
  asset,
  open,
  submitting,
  error,
  onClose,
  onSubmit,
}: StatusUpdateModalProps) {
  const t = useTranslations('inventory');
  const tCommon = useTranslations('common');
  const { getStatusCategoryLabel, statusOptionsByCategory } = useInventoryLabels();
  const [category, setCategory] = useState<StatusCategory>('availability');
  const [newStatus, setNewStatus] = useState('');
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (open) {
      setCategory('availability');
      setNewStatus('');
      setReason('');
    }
  }, [open, asset?.id]);

  if (!open || !asset) return null;

  const statusOptions = statusOptionsByCategory[category];

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!newStatus) return;
    onSubmit({
      status_category: category,
      new_status: newStatus,
      reason: reason.trim() || null,
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      title={t('statusUpdate.title')}
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>
            {tCommon('cancel')}
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={submitting || !newStatus}>
            {submitting ? tCommon('saving') : t('statusUpdate.submit')}
          </Button>
        </>
      }
    >
      <p className="inventory__modal-subtitle">
        {asset.display_id} · {asset.system_code}
      </p>
      {error && <p className="leads__state leads__state--error">{error}</p>}
      <form className="leads-form" onSubmit={handleSubmit}>
        <Select
          label={t('statusUpdate.category')}
          value={category}
          onChange={(event) => {
            setCategory(event.target.value as StatusCategory);
            setNewStatus('');
          }}
        >
          {STATUS_CATEGORIES.map((value) => (
            <option key={value} value={value}>
              {getStatusCategoryLabel(value)}
            </option>
          ))}
        </Select>
        <Select
          label={t('statusUpdate.newStatus')}
          value={newStatus}
          onChange={(event) => setNewStatus(event.target.value)}
        >
          <option value="">{t('statusUpdate.selectStatus')}</option>
          {statusOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
        <label className="ih-field">
          <span className="ih-field__label">{t('statusUpdate.reason')}</span>
          <textarea
            className="ih-input ih-input--textarea"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            rows={3}
          />
        </label>
      </form>
    </Dialog>
  );
}
