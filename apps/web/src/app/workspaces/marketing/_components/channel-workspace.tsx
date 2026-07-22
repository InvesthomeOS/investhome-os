'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo } from 'react';
import { useTranslations } from 'next-intl';

import { EmptyState, ErrorState, LoadingState, StatusChip, Button } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission, type MarketingPermissionAction } from '@/lib/marketing/marketing-permissions';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { SummaryWidget, UnavailableValue } from '../_components/summary-widget';

type ChannelRow = {
  id: string;
  name?: string | null;
  title?: string | null;
  status: string;
  readiness_state?: string;
  scheduled_at?: string | null;
};

type ChannelWorkspaceProps = {
  channelKey: 'social' | 'email' | 'whatsapp' | 'sms';
  permission: MarketingPermissionAction;
  createPermission?: MarketingPermissionAction;
  dashboardQuery: {
    isLoading: boolean;
    isError: boolean;
    data?: {
      provider_status?: { connected: boolean; status: string; message?: string | null };
      total_posts?: number;
      total_campaigns?: number;
      scheduled_posts?: number;
      scheduled_campaigns?: number;
    };
  };
  listQuery: {
    isLoading: boolean;
    isError: boolean;
    error: unknown;
    refetch: () => void;
    data?: { items: ChannelRow[]; total: number };
  };
  detailBasePath: string;
  createPath?: string;
  nameField?: 'name' | 'title';
};

export function ChannelWorkspace({
  channelKey,
  permission,
  createPermission,
  dashboardQuery,
  listQuery,
  detailBasePath,
  createPath,
  nameField = 'name',
}: ChannelWorkspaceProps) {
  const t = useTranslations(`marketing.channels.${channelKey}`);
  const tCommon = useTranslations('marketing.common');
  const tGlobal = useTranslations('common');
  const { user } = useAuth();
  const canView = hasMarketingPermission(user, permission);
  const canCreate = hasMarketingPermission(user, createPermission ?? permission);

  const dashboard = dashboardQuery.data;
  const providerConnected = dashboard?.provider_status?.connected ?? false;

  const columns = useMemo<AdminTableColumn<ChannelRow>[]>(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        render: (row) => {
          const label = String(row[nameField] ?? row.title ?? row.name ?? row.id);
          return <Link href={`${detailBasePath}/${row.id}` as Route}>{label}</Link>;
        },
      },
      {
        id: 'status',
        header: t('columns.status'),
        render: (row) => <StatusChip tone={row.status === 'scheduled' ? 'info' : 'default'}>{row.status}</StatusChip>,
      },
      {
        id: 'readiness',
        header: t('columns.readiness'),
        render: (row) =>
          row.readiness_state ? (
            <StatusChip tone={row.readiness_state === 'ready' ? 'success' : row.readiness_state === 'blocked' ? 'danger' : 'warning'}>
              {row.readiness_state}
            </StatusChip>
          ) : (
            <UnavailableValue label={tCommon('notCalculated')} />
          ),
      },
    ],
    [t, tCommon, detailBasePath, nameField],
  );

  if (!canView) {
    return (
      <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
    );
  }

  if (listQuery.isLoading || dashboardQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (listQuery.isError) {
    const err = listQuery.error;
    return (
      <ErrorState
        title={tCommon('error')}
        message={err instanceof ApiError ? err.message : tCommon('error')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            {tGlobal('retry')}
          </Button>
        }
      />
    );
  }

  const items = listQuery.data?.items ?? [];

  return (
    <main className="dashboard marketing-channel-workspace">
      <header className="dashboard__header dashboard__header--row">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        {createPath && canCreate ? (
          <Link href={createPath as Route} className="button">
            {t('create')}
          </Link>
        ) : null}
      </header>

      <div className="marketing-summary-row">
        <SummaryWidget
          title={t('summary.total')}
          state="ready"
          value={dashboard?.total_campaigns ?? dashboard?.total_posts ?? items.length}
        />
        <SummaryWidget
          title={t('summary.scheduled')}
          state="ready"
          value={dashboard?.scheduled_campaigns ?? dashboard?.scheduled_posts ?? 0}
        />
        <SummaryWidget
          title={t('summary.provider')}
          state="ready"
          value={
            providerConnected ? (
              tCommon('connected')
            ) : (
              <StatusChip tone="warning">{dashboard?.provider_status?.status ?? 'not_connected'}</StatusChip>
            )
          }
        />
        {!providerConnected ? (
          <SummaryWidget
            title={t('summary.providerMessage')}
            state="ready"
            value={dashboard?.provider_status?.message ?? tCommon('notConnected')}
          />
        ) : null}
      </div>

      {items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <AdminDataTable columns={columns} rows={items} rowKey={(row) => row.id} />
      )}
    </main>
  );
}
