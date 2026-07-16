'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog } from '@investhome/ui';

import type { WorkItem } from '@/lib/api/work-items';

interface CompleteWorkItemModalProps {
  item: WorkItem | null;
  open: boolean;
  onClose: () => void;
  onSubmit: (outcome: string, createNext: boolean) => Promise<void>;
}

export function CompleteWorkItemModal({ item, open, onClose, onSubmit }: CompleteWorkItemModalProps) {
  const t = useTranslations('work');
  const [outcome, setOutcome] = useState('');
  const [createNext, setCreateNext] = useState(false);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!item) return;
    setSaving(true);
    try {
      await onSubmit(outcome, createNext);
      onClose();
      setOutcome('');
      setCreateNext(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title={t('complete.title')}>
      <form className="sales-work-form" onSubmit={handleSubmit}>
        <p>{item?.title}</p>
        <label>
          {t('complete.outcome')}
          <textarea value={outcome} onChange={(e) => setOutcome(e.target.value)} rows={4} required />
        </label>
        <label className="sales-work-form__checkbox">
          <input type="checkbox" checked={createNext} onChange={(e) => setCreateNext(e.target.checked)} />
          {t('complete.createNext')}
        </label>
        <div className="sales-work-form__actions">
          <Button type="button" variant="secondary" onClick={onClose}>{t('form.cancel')}</Button>
          <Button type="submit" variant="primary" disabled={saving}>{t('complete.submit')}</Button>
        </div>
      </form>
    </Dialog>
  );
}
