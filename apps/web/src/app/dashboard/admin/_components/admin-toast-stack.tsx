'use client';

import { Alert, Button } from '@investhome/ui';
import { useTranslations } from 'next-intl';

import { useAdminToast, type AdminToastTone } from './use-admin-toast';

function toneToAlert(tone: AdminToastTone): 'success' | 'warning' | 'error' | 'info' {
  if (tone === 'success') return 'success';
  if (tone === 'warning') return 'warning';
  if (tone === 'permission') return 'warning';
  return 'error';
}

export function AdminToastStack() {
  const t = useTranslations('adminShell');
  const { toasts, dismissToast } = useAdminToast();

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div className="admin-toast-stack" role="region" aria-live="polite" aria-label={t('toastRegion')}>
      {toasts.map((toast) => (
        <div key={toast.id} className="admin-toast-stack__item">
          <Alert tone={toneToAlert(toast.tone)} role={toast.tone === 'error' ? 'alert' : 'status'}>
            {toast.tone === 'permission' ? (
              <>
                <strong>{t('permissionDenied')}: </strong>
                {toast.message}
              </>
            ) : (
              toast.message
            )}
          </Alert>
          <Button type="button" variant="ghost" size="sm" onClick={() => dismissToast(toast.id)}>
            {t('dismissToast')}
          </Button>
        </div>
      ))}
    </div>
  );
}
