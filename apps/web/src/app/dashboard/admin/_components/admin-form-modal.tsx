'use client';

import { Button, Dialog } from '@investhome/ui';
import { useTranslations } from 'next-intl';
import type { FormEvent, ReactNode } from 'react';

type AdminFormModalProps = {
  open: boolean;
  title: string;
  submitLabel: string;
  dirty?: boolean;
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>;
  children: ReactNode;
};

export function AdminFormModal({
  open,
  title,
  submitLabel,
  dirty = false,
  onClose,
  onSubmit,
  children,
}: AdminFormModalProps) {
  const tCommon = useTranslations('common');
  const t = useTranslations('adminShell');

  const handleClose = () => {
    if (dirty && !window.confirm(t('dirtyWarning'))) {
      return;
    }
    onClose();
  };

  if (!open) {
    return null;
  }

  return (
    <Dialog open={open} title={title} onClose={handleClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          void onSubmit(event);
        }}
      >
        {children}
        <div className="leads__modal-actions">
          <Button type="button" variant="secondary" onClick={handleClose}>
            {tCommon('cancel')}
          </Button>
          <Button type="submit">{submitLabel}</Button>
        </div>
      </form>
    </Dialog>
  );
}
