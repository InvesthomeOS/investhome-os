'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import {
  activateAutomation,
  archiveAutomation,
  automationQueries,
  automationQueryKeys,
  deleteAutomation,
  duplicateAutomation,
  pauseAutomation,
} from '@/workspaces/marketing/hooks/use-automations';

export default function AutomationDetailPage() {
  const params = useParams<{ automationId: string }>();
  const t = useTranslations('marketing.automations');
  const tStatus = useTranslations('marketing.automations.status');
  const tActions = useTranslations('marketing.automations.actions');
  const tCommon = useTranslations('marketing.common');
  const queryClient = useQueryClient();

  const detailQuery = useQuery(automationQueries.detail(params.automationId));
  const metricsQuery = useQuery(automationQueries.metrics(params.automationId));
  const executionsQuery = useQuery(automationQueries.executions(params.automationId));
  const logsQuery = useQuery(automationQueries.logs(params.automationId));

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: automationQueryKeys.detail(params.automationId) });
    void queryClient.invalidateQueries({ queryKey: automationQueryKeys.metrics(params.automationId) });
    void queryClient.invalidateQueries({ queryKey: automationQueryKeys.executions(params.automationId) });
    void queryClient.invalidateQueries({ queryKey: automationQueryKeys.logs(params.automationId) });
    void queryClient.invalidateQueries({ queryKey: automationQueryKeys.all });
  };

  const activateMutation = useMutation({ mutationFn: activateAutomation, onSuccess: invalidate });
  const pauseMutation = useMutation({ mutationFn: pauseAutomation, onSuccess: invalidate });
  const archiveMutation = useMutation({ mutationFn: archiveAutomation, onSuccess: invalidate });
  const duplicateMutation = useMutation({ mutationFn: duplicateAutomation, onSuccess: invalidate });
  const deleteMutation = useMutation({
    mutationFn: deleteAutomation,
    onSuccess: () => {
      window.location.href = '/workspaces/marketing/automations';
    },
  });

  if (detailQuery.isLoading) return <LoadingState label={tCommon('loading')} />;
  if (!detailQuery.data) return <EmptyState title={tCommon('error')} />;

  const automation = detailQuery.data;

  return (
    <main className="dashboard marketing-automation-detail">
      <header className="dashboard__header">
        <div>
          <Link href={'/workspaces/marketing/automations' as Route}>{t('title')}</Link>
          <h1 className="dashboard__title">{automation.name}</h1>
          <StatusChip tone={automation.status === 'active' ? 'success' : 'default'}>
            {tStatus.has(automation.status) ? tStatus(automation.status) : automation.status}
          </StatusChip>
        </div>
        <div className="marketing-automation-detail__actions">
          {(automation.status === 'draft' || automation.status === 'paused') && (
            <Button onClick={() => activateMutation.mutate(automation.id)}>{tActions('activate')}</Button>
          )}
          {automation.status === 'active' && (
            <Button variant="secondary" onClick={() => pauseMutation.mutate(automation.id)}>
              {tActions('pause')}
            </Button>
          )}
          {automation.status !== 'archived' && (
            <Button variant="ghost" onClick={() => archiveMutation.mutate(automation.id)}>
              {tActions('archive')}
            </Button>
          )}
          <Button variant="ghost" onClick={() => duplicateMutation.mutate(automation.id)}>
            {tActions('duplicate')}
          </Button>
          {automation.status !== 'active' && (
            <Button variant="ghost" onClick={() => deleteMutation.mutate(automation.id)}>
              {tActions('delete')}
            </Button>
          )}
        </div>
      </header>

      {!automation.execution_engine_available ? (
        <section className="marketing-dashboard__banner marketing-dashboard__banner--warning">
          <strong>{t('engineUnavailable')}</strong>
          <p>{metricsQuery.data?.execution_engine_message ?? t('engineUnavailableDescription')}</p>
        </section>
      ) : null}

      <section className="marketing-dashboard__section">
        <h2>{t('detail.trigger')}</h2>
        <pre>{JSON.stringify(automation.trigger, null, 2)}</pre>
      </section>

      <section className="marketing-dashboard__section">
        <h2>{t('detail.actions')}</h2>
        <pre>{JSON.stringify(automation.actions, null, 2)}</pre>
      </section>

      <section className="marketing-dashboard__section">
        <h2>{t('detail.metrics')}</h2>
        {metricsQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : (
          <ul>
            <li>
              {t('columns.executions')}: {metricsQuery.data?.execution_count ?? 0}
            </li>
            <li>
              {t('detail.notConnected')}: {metricsQuery.data?.not_connected_count ?? 0}
            </li>
          </ul>
        )}
      </section>

      <section className="marketing-dashboard__section">
        <h2>{t('detail.executions')}</h2>
        {executionsQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : (executionsQuery.data?.items.length ?? 0) === 0 ? (
          <EmptyState title={t('detail.noExecutions')} />
        ) : (
          <ul>
            {executionsQuery.data?.items.map((execution) => (
              <li key={execution.id}>
                {execution.status} — {execution.trigger_type ?? 'manual'} —{' '}
                {execution.created_at ? new Date(execution.created_at).toLocaleString() : ''}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="marketing-dashboard__section">
        <h2>{t('detail.logs')}</h2>
        {logsQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : (
          <ul>
            {logsQuery.data?.items.map((log) => (
              <li key={log.id}>
                [{log.level}] {log.message}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
