'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip, type StatusChipTone } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import {
  activateAutomation,
  archiveAutomation,
  automationQueries,
  automationQueryKeys,
  deleteAutomation,
  duplicateAutomation,
  pauseAutomation,
} from '@/workspaces/marketing/hooks/use-automations';
import type { AutomationSummary } from '@/workspaces/marketing/api/automations';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { UnavailableValue } from '../../_components/summary-widget';

function statusTone(status: string): StatusChipTone {
  switch (status) {
    case 'active':
      return 'success';
    case 'paused':
    case 'error':
      return 'warning';
    case 'archived':
      return 'danger';
    default:
      return 'default';
  }
}

export function AutomationsWorkspace() {
  const t = useTranslations('marketing.automations');
  const tStatus = useTranslations('marketing.automations.status');
  const tCommon = useTranslations('marketing.common');
  const tActions = useTranslations('marketing.automations.actions');
  const { user } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);

  const listQuery = useQuery(automationQueries.list({ page, page_size: 25 }));

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: automationQueryKeys.all });
  };

  const activateMutation = useMutation({
    mutationFn: activateAutomation,
    onSuccess: invalidate,
  });
  const pauseMutation = useMutation({
    mutationFn: pauseAutomation,
    onSuccess: invalidate,
  });
  const archiveMutation = useMutation({
    mutationFn: archiveAutomation,
    onSuccess: invalidate,
  });
  const duplicateMutation = useMutation({
    mutationFn: duplicateAutomation,
    onSuccess: (data) => {
      invalidate();
      router.push(`/workspaces/marketing/automations/${data.id}` as Route);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteAutomation,
    onSuccess: invalidate,
  });

  const columns = useMemo<AdminTableColumn<AutomationSummary>[]>(
    () => [
      {
        id: 'name',
        header: t('columns.name'),
        render: (row) => (
          <Link href={`/workspaces/marketing/automations/${row.id}` as Route}>{row.name}</Link>
        ),
      },
      {
        id: 'status',
        header: t('columns.status'),
        render: (row) => (
          <StatusChip tone={statusTone(row.status)}>
            {tStatus.has(row.status) ? tStatus(row.status) : row.status}
          </StatusChip>
        ),
      },
      {
        id: 'executions',
        header: t('columns.executions'),
        render: (row) => String(row.execution_count),
      },
      {
        id: 'lastRun',
        header: t('columns.lastRun'),
        render: (row) =>
          row.last_run_at ? (
            new Date(row.last_run_at).toLocaleString()
          ) : (
            <UnavailableValue label={tCommon('notCalculated')} />
          ),
      },
      {
        id: 'actions',
        header: tActions('activate'),
        render: (row) => (
          <div className="marketing-automations__row-actions">
            {row.status === 'draft' || row.status === 'paused' ? (
              <Button variant="secondary" onClick={() => activateMutation.mutate(row.id)}>
                {tActions('activate')}
              </Button>
            ) : null}
            {row.status === 'active' ? (
              <Button variant="secondary" onClick={() => pauseMutation.mutate(row.id)}>
                {tActions('pause')}
              </Button>
            ) : null}
            {row.status !== 'archived' ? (
              <Button variant="ghost" onClick={() => archiveMutation.mutate(row.id)}>
                {tActions('archive')}
              </Button>
            ) : null}
            <Button variant="ghost" onClick={() => duplicateMutation.mutate(row.id)}>
              {tActions('duplicate')}
            </Button>
            {row.status !== 'active' ? (
              <Button variant="ghost" onClick={() => deleteMutation.mutate(row.id)}>
                {tActions('delete')}
              </Button>
            ) : null}
          </div>
        ),
      },
    ],
    [t, tStatus, tCommon, tActions, activateMutation, pauseMutation, archiveMutation, duplicateMutation, deleteMutation],
  );

  if (!hasMarketingPermission(user, 'manage_automations')) {
    return (
      <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
    );
  }

  if (listQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (listQuery.isError) {
    return (
      <ErrorState
        title={tCommon('error')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : tCommon('error')}
      />
    );
  }

  const items = listQuery.data?.items ?? [];

  return (
    <main className="dashboard marketing-automations">
      <header className="dashboard__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </div>
        <Button onClick={() => router.push('/workspaces/marketing/automations/new' as Route)}>{t('create')}</Button>
      </header>

      {!listQuery.data?.items.some((row) => row.execution_engine_available) ? (
        <section className="marketing-dashboard__banner marketing-dashboard__banner--warning">
          <strong>{t('engineUnavailable')}</strong>
          <p>{t('engineUnavailableDescription')}</p>
        </section>
      ) : null}

      {items.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <AdminDataTable columns={columns} rows={items} rowKey={(row) => row.id} />
      )}

      {(listQuery.data?.pages ?? 0) > 1 ? (
        <div className="marketing-automations__pagination">
          <Button variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span>
            {page} / {listQuery.data?.pages}
          </span>
          <Button
            variant="ghost"
            disabled={page >= (listQuery.data?.pages ?? 1)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      ) : null}
    </main>
  );
}
