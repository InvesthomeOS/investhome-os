'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchAutomationOverview,
  type AutomationOverview,
} from '@/lib/api/automation-center';

import { AutomationShell } from './automation-shell';
import { formatDateTime, formatDuration, formatSuccessRate } from './format';

export function AutomationOverviewWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [data, setData] = useState<AutomationOverview | null>(null);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationOverview()
      .then((response) => {
        if (!cancelled) {
          setData(response);
          setState('success');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setData(null);
          setState('error');
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <AutomationShell title={t('title')} subtitle={t('subtitle')}>
      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}

      {state === 'success' && data ? (
        <>
          {!data.health.execution_engine_available ? (
            <div className="automation-center__banner automation-center__banner--warn" role="status">
              {data.health.execution_engine_message || t('engineUnavailable')}
            </div>
          ) : null}

          <section className="automation-center__kpis" aria-label={t('sections.systemHealth')}>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('health.availability')}</p>
              <p className="automation-center__kpi-value">
                {t(`availability.${data.health.availability}`)}
              </p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('health.running')}</p>
              <p className="automation-center__kpi-value">{data.health.running_count}</p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('health.failed')}</p>
              <p className="automation-center__kpi-value">{data.health.failed_count}</p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('health.avgRuntime')}</p>
              <p className="automation-center__kpi-value">
                {formatDuration(data.health.average_runtime_ms)}
              </p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('health.queueSize')}</p>
              <p className="automation-center__kpi-value">
                {data.health.queue_available && data.health.queue_size != null
                  ? data.health.queue_size
                  : t('unavailable')}
              </p>
              <p className="automation-center__kpi-hint">
                {data.queue_health.redis_connected ? t('health.redisOk') : t('health.redisDown')}
              </p>
            </div>
            <div className="automation-center__kpi">
              <p className="automation-center__kpi-label">{t('health.lastExecution')}</p>
              <p className="automation-center__kpi-value" style={{ fontSize: '1rem' }}>
                {formatDateTime(data.health.last_execution_at, locale)}
              </p>
            </div>
          </section>

          <div className="automation-center__grid">
            <section className="automation-center__panel">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.workflowStatus')}</h2>
                <Link href={'/dashboard/automation/workflows' as Route} className="automation-center__panel-link">
                  {t('viewAll')}
                </Link>
              </div>
              {data.workflow_status.length === 0 ? (
                <p className="automation-center__empty">{t('empty.executions')}</p>
              ) : (
                <ul style={{ listStyle: 'none', display: 'grid', gap: '0.45rem' }}>
                  {data.workflow_status.map((row) => (
                    <li key={row.status} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                      <span>{t.has(`executionStatus.${row.status}`) ? t(`executionStatus.${row.status}`) : row.status}</span>
                      <strong>{row.count}</strong>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="automation-center__panel">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.queueHealth')}</h2>
              </div>
              <p>{data.queue_health.message}</p>
              <p className="automation-center__muted" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
                {t('health.registeredJobs', { count: data.queue_health.jobs.length })}
              </p>
            </section>

            <section className="automation-center__panel automation-center__panel--full">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.executionHistory')}</h2>
                <Link href={'/dashboard/automation/executions' as Route} className="automation-center__panel-link">
                  {t('viewAll')}
                </Link>
              </div>
              {data.recent_executions.length === 0 ? (
                <EmptyState title={t('empty.executions')} description={t('empty.executionsHint')} />
              ) : (
                <div className="automation-center__table-wrap">
                  <table className="automation-center__table">
                    <thead>
                      <tr>
                        <th>{t('columns.workflow')}</th>
                        <th>{t('columns.status')}</th>
                        <th>{t('columns.duration')}</th>
                        <th>{t('columns.retries')}</th>
                        <th>{t('columns.time')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_executions.map((row) => (
                        <tr key={row.id}>
                          <td>
                            <Link href={`/dashboard/automation/workflows/${row.workflow_id}` as Route}>
                              {row.workflow_name || row.workflow_id}
                            </Link>
                          </td>
                          <td>
                            <StatusChip tone={row.status === 'failed' ? 'danger' : row.status === 'completed' ? 'success' : 'default'}>
                              {t.has(`executionStatus.${row.status}`) ? t(`executionStatus.${row.status}`) : row.status}
                            </StatusChip>
                          </td>
                          <td>{formatDuration(row.duration_ms)}</td>
                          <td>{row.retry_count}</td>
                          <td>{formatDateTime(row.created_at, locale)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="automation-center__panel">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.recentFailures')}</h2>
                <Link href={'/dashboard/automation/errors' as Route} className="automation-center__panel-link">
                  {t('viewAll')}
                </Link>
              </div>
              {data.recent_failures.length === 0 ? (
                <p className="automation-center__empty">{t('empty.errors')}</p>
              ) : (
                <ul style={{ listStyle: 'none', display: 'grid', gap: '0.65rem' }}>
                  {data.recent_failures.map((row) => (
                    <li key={row.id}>
                      <strong>{row.workflow_name || row.workflow_id}</strong>
                      <p className="automation-center__muted" style={{ margin: '0.2rem 0 0', fontSize: '0.85rem' }}>
                        {row.message}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="automation-center__panel">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.scheduledJobs')}</h2>
                <Link href={'/dashboard/automation/schedules' as Route} className="automation-center__panel-link">
                  {t('viewAll')}
                </Link>
              </div>
              {data.scheduled_jobs.length === 0 ? (
                <p className="automation-center__empty">{t('empty.schedules')}</p>
              ) : (
                <ul style={{ listStyle: 'none', display: 'grid', gap: '0.55rem' }}>
                  {data.scheduled_jobs.slice(0, 6).map((job) => (
                    <li key={job.id} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                      <span>{job.name}</span>
                      <span className="automation-center__muted">{job.cadence_label}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="automation-center__panel">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.aiWorkflows')}</h2>
              </div>
              {data.ai_workflows.length === 0 ? (
                <p className="automation-center__empty">{t('empty.ai')}</p>
              ) : (
                <ul style={{ listStyle: 'none', display: 'grid', gap: '0.55rem' }}>
                  {data.ai_workflows.map((wf) => (
                    <li key={wf.id}>
                      <Link href={`/dashboard/automation/workflows/${encodeURIComponent(wf.id)}` as Route}>
                        {wf.name}
                      </Link>
                      <p className="automation-center__muted" style={{ margin: '0.2rem 0 0', fontSize: '0.8rem' }}>
                        {formatSuccessRate(wf.success_rate, wf.success_rate_available, t('unavailable'))}
                        {wf.is_placeholder ? ` · ${t('placeholder')}` : null}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="automation-center__panel">
              <div className="automation-center__panel-head">
                <h2 className="automation-center__panel-title">{t('sections.integrations')}</h2>
                <Link href={'/dashboard/automation/integrations' as Route} className="automation-center__panel-link">
                  {t('viewAll')}
                </Link>
              </div>
              <div className="automation-center__integration-grid">
                {data.integrations.slice(0, 6).map((item) => (
                  <div key={item.id} className="automation-center__integration">
                    <h3>{item.name}</h3>
                    <StatusChip
                      tone={
                        item.status === 'connected'
                          ? 'success'
                          : item.status === 'configured'
                            ? 'warning'
                            : 'default'
                      }
                    >
                      {t.has(`integrationStatus.${item.status}`)
                        ? t(`integrationStatus.${item.status}`)
                        : item.status}
                    </StatusChip>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      ) : null}
    </AutomationShell>
  );
}
