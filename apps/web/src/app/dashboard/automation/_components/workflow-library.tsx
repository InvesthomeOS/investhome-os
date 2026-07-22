'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchAutomationWorkflows,
  type AutomationWorkflowSummary,
  type WorkflowCategory,
} from '@/lib/api/automation-center';

import { AutomationShell } from './automation-shell';
import { formatDateTime, formatSuccessRate } from './format';

const CATEGORIES: WorkflowCategory[] = [
  'crm',
  'marketing',
  'investor',
  'finance',
  'projects',
  'website',
  'ai',
  'notifications',
  'administration',
];

export function WorkflowLibraryWorkspace() {
  const t = useTranslations('automation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const [items, setItems] = useState<AutomationWorkflowSummary[]>([]);
  const [state, setState] = useState<'loading' | 'error' | 'success'>('loading');
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    void fetchAutomationWorkflows({
      page: 1,
      page_size: 100,
      category: category || undefined,
      search: appliedSearch || undefined,
    })
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
  }, [category, appliedSearch]);

  return (
    <AutomationShell title={t('workflows.title')} subtitle={t('workflows.subtitle')}>
      <div className="automation-center__filters">
        <label>
          {t('filters.category')}
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">{t('filters.allCategories')}</option>
            {CATEGORIES.map((value) => (
              <option key={value} value={value}>
                {t(`categories.${value}`)}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t('filters.search')}
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') setAppliedSearch(search.trim());
            }}
            placeholder={t('filters.searchPlaceholder')}
          />
        </label>
        <button type="button" className="leads__button leads__button--secondary" onClick={() => setAppliedSearch(search.trim())}>
          {t('filters.apply')}
        </button>
      </div>

      {state === 'loading' ? <LoadingState label={tCommon('loading')} /> : null}
      {state === 'error' ? <ErrorState title={t('loadError')} message={t('loadErrorHint')} /> : null}

      {state === 'success' && items.length === 0 ? (
        <EmptyState title={t('empty.workflows')} description={t('empty.workflowsHint')} />
      ) : null}

      {state === 'success' && items.length > 0 ? (
        <div className="automation-center__panel automation-center__panel--full" style={{ gridColumn: 'unset' }}>
          <div className="automation-center__table-wrap">
            <table className="automation-center__table">
              <thead>
                <tr>
                  <th>{t('columns.name')}</th>
                  <th>{t('columns.category')}</th>
                  <th>{t('columns.status')}</th>
                  <th>{t('columns.trigger')}</th>
                  <th>{t('columns.lastRun')}</th>
                  <th>{t('columns.nextRun')}</th>
                  <th>{t('columns.successRate')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <Link href={`/dashboard/automation/workflows/${encodeURIComponent(row.id)}` as Route}>
                        {row.name}
                      </Link>
                      {row.is_placeholder ? (
                        <div className="automation-center__muted" style={{ fontSize: '0.75rem' }}>
                          {t('placeholder')}
                        </div>
                      ) : null}
                    </td>
                    <td>{t(`categories.${row.category}`)}</td>
                    <td>
                      <StatusChip tone={row.status === 'active' || row.status === 'scheduled' ? 'success' : 'default'}>
                        {t.has(`workflowStatus.${row.status}`) ? t(`workflowStatus.${row.status}`) : row.status}
                      </StatusChip>
                    </td>
                    <td>{row.trigger_label || row.trigger || '—'}</td>
                    <td>{formatDateTime(row.last_run_at, locale)}</td>
                    <td>{row.next_run_label || t('unavailable')}</td>
                    <td>{formatSuccessRate(row.success_rate, row.success_rate_available, t('unavailable'))}</td>
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
