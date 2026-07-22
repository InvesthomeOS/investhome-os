'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchAutomationExecutions,
  type AutomationExecutionItem,
} from '@/lib/api/automation-center';

import { AutomationShell } from './automation-shell';
import { formatDateTime, formatDuration } from './format';

export function ExecutionMonitorWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [items, setItems] = useState<AutomationExecutionItem[]>([]);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
  const [status, setStatus] = useState('');
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationExecutions({ page: 1, page_size: 50, status: status || undefined })
      .then((response) => {
        if (!cancelled) {
          setItems(response.items);
          setStatusCounts(response.status_counts);
          setState('success');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
          setState('error');
        }
      });
    return () => {
      cancelled = true;
    };
  }, [status]);

  return (
    <AutomationShell title={t('executions.title')} subtitle={t('executions.subtitle')}>
      <section className="automation-center__kpis" aria-label={t('sections.workflowStatus')}>
        {['running', 'queued', 'completed', 'failed', 'cancelled', 'not_connected'].map((key) => (
          <div key={key} className="automation-center__kpi">
            <p className="automation-center__kpi-label">
              {t.has(`executionStatus.${key}`) ? t(`executionStatus.${key}`) : key}
            </p>
            <p className="automation-center__kpi-value">{statusCounts[key] ?? 0}</p>
          </div>
        ))}
      </section>

      <div className="automation-center__filters">
        <label>
          {t('filters.status')}
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">{t('filters.allStatuses')}</option>
            {Object.keys(statusCounts).map((key) => (
              <option key={key} value={key}>
                {t.has(`executionStatus.${key}`) ? t(`executionStatus.${key}`) : key}
              </option>
            ))}
          </select>
        </label>
      </div>

      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}
      {state === 'success' && items.length === 0 ? (
        <EmptyState title={t('empty.executions')} description={t('empty.executionsHint')} />
      ) : null}

      {state === 'success' && items.length > 0 ? (
        <div className="automation-center__panel automation-center__panel--full" style={{ gridColumn: 'unset' }}>
          <div className="automation-center__table-wrap">
            <table className="automation-center__table">
              <thead>
                <tr>
                  <th>{t('columns.workflow')}</th>
                  <th>{t('columns.status')}</th>
                  <th>{t('columns.trigger')}</th>
                  <th>{t('columns.retries')}</th>
                  <th>{t('columns.duration')}</th>
                  <th>{t('columns.time')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
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
                    <td>{row.trigger_type || '—'}</td>
                    <td>{row.retry_count}</td>
                    <td>{formatDuration(row.duration_ms)}</td>
                    <td>{formatDateTime(row.created_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </AutomationShell>
  );
}
