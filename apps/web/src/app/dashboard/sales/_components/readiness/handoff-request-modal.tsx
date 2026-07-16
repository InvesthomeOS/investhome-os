'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog } from '@investhome/ui';

interface HandoffRequestModalProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (notes: string) => void;
  loading?: boolean;
}

export function HandoffRequestModal({ open, onClose, onSubmit, loading }: HandoffRequestModalProps) {
  const t = useTranslations('salesReadiness');
  const [notes, setNotes] = useState('');

  return (
    <Dialog open={open} onClose={onClose} title={t('handoff.requestTitle')}>
      <p>{t('handoff.requestDescription')}</p>
      <label className="ih-field">
        <span>{t('handoff.notes')}</span>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
      </label>
      <div className="ih-dialog__actions">
        <Button variant="secondary" onClick={onClose}>{t('handoff.cancel')}</Button>
        <Button variant="primary" disabled={loading} onClick={() => onSubmit(notes)}>{t('handoff.requestSubmit')}</Button>
      </div>
    </Dialog>
  );
}
