'use client';

import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { fetchAutomationAudit, type AutomationAuditItem } from '@/lib/api/automation-center';

import { AutomationShell } from './automation-shell';
import { formatDateTime } from './format';

export function AuditLogWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [items, setItems] = useState<AutomationAuditItem[]>([]);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationAudit({ page: 1, page_size: 50 })
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
    <AutomationShell title={t('audit.title')} subtitle={t('audit.subtitle')}>
      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}
      {state === 'success' && items.length === 0 ? (
        <EmptyState title={t('empty.audit')} description={t('empty.auditHint')} />
      ) : null}

      {state === 'success' && items.length > 0 ? (
        <div className="automation-center__panel automation-center__panel--full" style={{ gridColumn: 'unset' }}>
          <div className="automation-center__table-wrap">
            <table className="automation-center__table">
              <thead>
                <tr>
                  <th>{t('columns.time')}</th>
                  <th>{t('columns.action')}</th>
                  <th>{t('columns.workflow')}</th>
                  <th>{t('columns.actor')}</th>
                  <th>{t('columns.message')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDateTime(row.created_at, locale)}</td>
                    <td>
                      <StatusChip tone="default">
                        {t.has(`auditActions.${row.action}`) ? t(`auditActions.${row.action}`) : row.action}
                      </StatusChip>
                    </td>
                    <td>{row.entity_label || row.entity_id || '—'}</td>
                    <td>{row.actor_name || t('audit.system')}</td>
                    <td>{row.description_key || '—'}</td>
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
