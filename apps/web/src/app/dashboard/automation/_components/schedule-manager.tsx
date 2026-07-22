'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchAutomationSchedules,
  type AutomationScheduleItem,
} from '@/lib/api/automation-center';

import { AutomationShell } from './automation-shell';
import { formatDateTime } from './format';

export function ScheduleManagerWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [items, setItems] = useState<AutomationScheduleItem[]>([]);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationSchedules()
      .then((response) => {
        if (!cancelled) {
          setItems(response.items);
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
  }, []);

  return (
    <AutomationShell title={t('schedules.title')} subtitle={t('schedules.subtitle')}>
      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}
      {state === 'success' && items.length === 0 ? (
        <EmptyState title={t('empty.schedules')} description={t('empty.schedulesHint')} />
      ) : null}

      {state === 'success' && items.length > 0 ? (
        <div className="automation-center__panel automation-center__panel--full" style={{ gridColumn: 'unset' }}>
          <div className="automation-center__table-wrap">
            <table className="automation-center__table">
              <thead>
                <tr>
                  <th>{t('columns.name')}</th>
                  <th>{t('columns.category')}</th>
                  <th>{t('columns.cadence')}</th>
                  <th>{t('columns.cron')}</th>
                  <th>{t('columns.nextRun')}</th>
                  <th>{t('columns.lastRun')}</th>
                  <th>{t('columns.status')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <Link href={`/dashboard/automation/workflows/${encodeURIComponent(row.id)}` as Route}>
                        {row.name}
                      </Link>
                      {row.description ? (
                        <div className="automation-center__muted" style={{ fontSize: '0.75rem', marginTop: '0.2rem' }}>
                          {row.description}
                        </div>
                      ) : null}
                    </td>
                    <td>{t(`categories.${row.category}`)}</td>
                    <td>
                      {t.has(`cadence.${row.cadence}`) ? t(`cadence.${row.cadence}`) : row.cadence_label}
                    </td>
                    <td>{row.cron_expression || '—'}</td>
                    <td>{row.next_run_label || t('unavailable')}</td>
                    <td>{formatDateTime(row.last_run_at, locale)}</td>
                    <td>
                      <StatusChip tone="default">
                        {t.has(`workflowStatus.${row.status}`) ? t(`workflowStatus.${row.status}`) : row.status}
                      </StatusChip>
                    </td>
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
