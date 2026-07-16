'use client';

import { useTranslations } from 'next-intl';

import { Button, Dialog } from '@investhome/ui';

interface HandoffApproveModalProps {
  open: boolean;
  caseCode: string;
  onClose: () => void;
  onApprove: () => void;
  onReturn: () => void;
  loading?: boolean;
}

export function HandoffApproveModal({
  open,
  caseCode,
  onClose,
  onApprove,
  onReturn,
  loading,
}: HandoffApproveModalProps) {
  const t = useTranslations('salesReadiness');

  return (
    <Dialog open={open} onClose={onClose} title={t('handoff.approveTitle')}>
      <p>{t('handoff.approveDescription', { caseCode })}</p>
      <div className="ih-dialog__actions">
        <Button variant="secondary" onClick={onReturn}>{t('handoff.return')}</Button>
        <Button variant="primary" disabled={loading} onClick={onApprove}>{t('handoff.approveSubmit')}</Button>
      </div>
    </Dialog>
  );
}
