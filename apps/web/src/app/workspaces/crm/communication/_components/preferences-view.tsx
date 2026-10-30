'use client';

import { useLocale, useTranslations } from 'next-intl';

import { Alert, EmptyState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';

export function PreferencesView() {
  const t = useTranslations('crm.communication.preferences');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const tr = locale.startsWith('tr');
  const { authLoading, canViewCommunications } = useCrmAccess();

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return <Alert tone="error">{t('accessDenied')}</Alert>;
  }

  return (
    <div className="crm-communication-subview" data-testid="crm-preferences-unavailable">
      <EmptyState
        title={tr ? 'Tercihler burada yok' : 'Preferences are not available here'}
        description={
          tr
            ? 'Kanal tercihleri kişi veya şirket kaydına bağlı bir akış olmadan düzenlenemez.'
            : 'Channel preferences cannot be edited until they are tied to a person or company record.'
        }
      />
    </div>
  );
}
