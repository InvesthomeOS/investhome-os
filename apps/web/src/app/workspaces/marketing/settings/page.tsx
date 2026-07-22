'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';

export default function MarketingSettingsPage() {
  const t = useTranslations('marketing.settingsModule');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();
  const canManage = hasMarketingPermission(user, 'manage_settings');

  const providersQuery = useQuery({
    ...marketingQueries.providerStatuses(),
    enabled: canManage,
  });

  if (!canManage) {
    return (
      <main className="dashboard marketing-module-shell">
        <header className="dashboard__header">
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </header>
        <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
      </main>
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header">
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('description')}</p>
      </header>

      {providersQuery.isLoading ? (
        <LoadingState label={tCommon('loading')} />
      ) : providersQuery.isError ? (
        <ErrorState
          title={tCommon('error')}
          message={providersQuery.error instanceof ApiError ? providersQuery.error.message : tCommon('error')}
        />
      ) : (providersQuery.data?.providers ?? []).length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>{t('columns.channel')}</th>
              <th>{t('columns.provider')}</th>
              <th>{t('columns.status')}</th>
            </tr>
          </thead>
          <tbody>
            {providersQuery.data?.providers.map((provider) => (
              <tr key={provider.channel_id}>
                <td>{provider.channel_name}</td>
                <td>{provider.provider ?? tCommon('noData')}</td>
                <td>
                  <StatusChip tone={provider.connection_status === 'connected' ? 'success' : 'default'}>
                    {provider.connection_status}
                  </StatusChip>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
