'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchAutomationErrors,
  retryAutomationError,
  type AutomationErrorItem,
} from '@/lib/api/automation-center';
import { canManageAutomation } from '@/lib/automation/automation-permissions';
import { useAuth } from '@/lib/auth/auth-context';

import { AutomationShell } from './automation-shell';
import { formatDateTime } from './format';

export function ErrorCenterWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const canManage = canManageAutomation(user);
  const [items, setItems] = useState<AutomationErrorItem[]>([]);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');
  const [retryMessage, setRetryMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationErrors({ page: 1, page_size: 50 })
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

  const handleRetry = async (id: string) => {
    setRetryMessage(null);
    try {
      const result = await retryAutomationError(id);
      setRetryMessage(result.message);
    } catch {
      setRetryMessage(t('errors.retryFailed'));
    }
  };

  return (
    <AutomationShell title={t('errors.title')} subtitle={t('errors.subtitle')}>
      {retryMessage ? (
        <div className="automation-center__banner automation-center__banner--warn" role="status">
          {retryMessage}
        </div>
      ) : null}

      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}
      {state === 'success' && items.length === 0 ? (
        <EmptyState title={t('empty.errors')} description={t('empty.errorsHint')} />
      ) : null}

      {state === 'success' && items.length > 0 ? (
        <div className="automation-center__panel automation-center__panel--full" style={{ gridColumn: 'unset' }}>
          <div className="automation-center__table-wrap">
            <table className="automation-center__table">
              <thead>
                <tr>
                  <th>{t('columns.workflow')}</th>
                  <th>{t('columns.time')}</th>
                  <th>{t('columns.severity')}</th>
                  <th>{t('columns.message')}</th>
                  <th>{t('columns.retries')}</th>
                  <th>{t('columns.actions')}</th>
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
                    <td>{formatDateTime(row.time, locale)}</td>
                    <td>
                      <StatusChip tone={row.severity === 'error' || row.severity === 'critical' ? 'danger' : 'warning'}>
                        {t.has(`severity.${row.severity}`) ? t(`severity.${row.severity}`) : row.severity}
                      </StatusChip>
                    </td>
                    <td>{row.message}</td>
                    <td>{row.retry_count}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                        <Link
                          href={`/dashboard/automation/workflows/${row.workflow_id}` as Route}
                          className="automation-center__panel-link"
                        >
                          {t('errors.viewDetails')}
                        </Link>
                        {canManage ? (
                          <Button variant="ghost" onClick={() => void handleRetry(row.id)}>
                            {t('errors.retry')}
                          </Button>
                        ) : null}
                      </div>
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
