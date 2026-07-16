'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Dialog } from '@investhome/ui';

interface WaiverModalProps {
  open: boolean;
  requirementTitle: string;
  onClose: () => void;
  onSubmit: (reason: string) => void;
  loading?: boolean;
}

export function WaiverModal({ open, requirementTitle, onClose, onSubmit, loading }: WaiverModalProps) {
  const t = useTranslations('salesReadiness');
  const [reason, setReason] = useState('');

  return (
    <Dialog open={open} onClose={onClose} title={t('waiver.title')}>
      <p>{t('waiver.description', { title: requirementTitle })}</p>
      <label className="ih-field">
        <span>{t('waiver.reason')}</span>
        <textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={4} required />
      </label>
      <div className="ih-dialog__actions">
        <Button variant="secondary" onClick={onClose}>{t('waiver.cancel')}</Button>
        <Button
          variant="primary"
          disabled={!reason.trim() || loading}
          onClick={() => onSubmit(reason.trim())}
        >
          {t('waiver.submit')}
        </Button>
      </div>
    </Dialog>
  );
}
