'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  fetchLeads,
  formatBudget,
  formatDate,
  type Lead,
  type LeadFilters,
  type LeadStatus,
} from '@/lib/api/leads';
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { useAuth } from '@/lib/auth/auth-context';
import { hasPermission } from '@/lib/api/auth';

import { CrmAnalyticsStrip } from './crm-analytics-strip';
import { CrmDrawerField, CrmRecordDrawer } from './crm-record-drawer';

const FILTER_KEY = 'investhome.crm.g2.leads.filters';
const SAVED_VIEWS = [
  { id: 'all', status: '' as const },
  { id: 'new', status: 'New' as LeadStatus },
  { id: 'qualified', status: 'Qualified' as LeadStatus },
  { id: 'meeting', status: 'Meeting Scheduled' as LeadStatus },
  { id: 'won', status: 'Won' as LeadStatus },
] as const;

type SortKey =
  | 'full_name'
  | 'company'
  | 'status'
  | 'estimated_budget'
  | 'country'
  | 'assigned_to'
  | 'created_at'
  | 'updated_at';

type SortDir = 'asc' | 'desc';

const DEMO_LEADS: Lead[] = [
  {
    id: 'demo-lead-1',
    full_name: 'Ayşe Demir',
    email: 'ayse@example.com',
    phone: '+90 532 000 0001',
    country: 'TR',
    source: 'Website',
    status: 'Qualified',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Demir Holding',
    preferred_market: 'Istanbul',
    cached_lead_score: 82,
    estimated_budget: '450000',
    interested_project: 'Marina Residences',
    notes: 'Demo kayıt — API yoksa gösterilir.',
    is_demo: true,
    archived_at: null,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-07-18T14:00:00Z',
  },
  {
    id: 'demo-lead-2',
    full_name: 'James Carter',
    email: 'james@example.com',
    phone: null,
    country: 'GB',
    source: 'Referral',
    status: 'Meeting Scheduled',
    assigned_to: 'Sales B',
    assigned_manager_id: null,
    company: 'Carter Capital',
    preferred_market: 'London',
    cached_lead_score: 74,
    estimated_budget: '1200000',
    interested_project: 'Skyline Tower',
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: '2026-06-12T09:00:00Z',
    updated_at: '2026-07-19T11:00:00Z',
  },
  {
    id: 'demo-lead-3',
    full_name: 'Fatima Al-Hassan',
    email: 'fatima@example.com',
    phone: '+971 50 000 0003',
    country: 'AE',
    source: 'Exhibition',
    status: 'New',
    assigned_to: 'Sales A',
    assigned_manager_id: null,
    company: 'Gulf Property Group',
    preferred_market: 'Dubai',
    cached_lead_score: 61,
    estimated_budget: '890000',
    interested_project: null,
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: '2026-07-01T08:00:00Z',
    updated_at: '2026-07-15T16:00:00Z',
  },
];

function loadFilters(): LeadFilters {
  if (typeof window === 'undefined') return { search: '', status: '' };
  try {
    const raw = localStorage.getItem(FILTER_KEY);
    if (!raw) return { search: '', status: '' };
    return { search: '', status: '', ...JSON.parse(raw) };
  } catch {
    return { search: '', status: '' };
  }
}

function priorityFromScore(score: number | null): 'low' | 'normal' | 'high' | 'urgent' {
  if (score == null) return 'normal';
  if (score >= 85) return 'urgent';
  if (score >= 70) return 'high';
  if (score >= 40) return 'normal';
  return 'low';
}

export function CrmLeadsWorkspace() {
  const t = useTranslations('crm.g2.leads');
  const tDrawer = useTranslations('crm.g2.drawer');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStatusLabel, statusOptions } = useLeadLabels();
  const { user } = useAuth();

  const canView = user
    ? hasPermission(user, 'leads', 'view') || hasPermission(user, 'sales', 'view')
    : false;

  const [filters, setFilters] = useState<LeadFilters>({ search: '', status: '' });
  const [applied, setApplied] = useState<LeadFilters>({ search: '', status: '' });
  const [leads, setLeads] = useState<Lead[]>([]);
  const [usingDemo, setUsingDemo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [sortKey, setSortKey] = useState<SortKey>('updated_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [page, setPage] = useState(1);
  const [drawerLead, setDrawerLead] = useState<Lead | null>(null);
  const pageSize = 25;

  useEffect(() => {
    const stored = loadFilters();
    setFilters(stored);
    setApplied(stored);
  }, []);

  const load = useCallback(
    async (next: LeadFilters) => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchLeads(next);
        if (res.items.length === 0 && !next.search && !next.status) {
          setLeads(DEMO_LEADS);
          setUsingDemo(true);
        } else {
          setLeads(res.items);
          setUsingDemo(false);
        }
      } catch {
        setLeads(DEMO_LEADS);
        setUsingDemo(true);
        setError(null);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    void load(applied);
    try {
      localStorage.setItem(FILTER_KEY, JSON.stringify(applied));
    } catch {
      /* ignore */
    }
  }, [applied, canView, load]);

  const sorted = useMemo(() => {
    const rows = [...leads];
    rows.sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      const cmp = String(av).localeCompare(String(bv), locale, { numeric: true });
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return rows;
  }, [leads, sortKey, sortDir, locale]);

  const pageRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [sorted, page]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleAll = () => {
    if (selectedIds.length === pageRows.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(pageRows.map((r) => r.id));
    }
  };

  if (!user) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  if (loading) {
    return <LoadingState label={t('loading')} variant="skeleton" lines={8} />;
  }

  if (error) {
    return (
      <ErrorState
        title={t('loadError')}
        message={error}
        action={
          <Button type="button" onClick={() => void load(applied)}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  return (
    <div className="crm-g2-leads" data-testid="crm-g2-leads">
      <header className="crm-g2-toolbar">
        <div>
          <p className="crm-g2-toolbar__eyebrow">{t('eyebrow')}</p>
          <h1 className="crm-g2-toolbar__title">{t('title')}</h1>
          <p className="crm-g2-toolbar__subtitle">
            {t('subtitle', { count: sorted.length })}
            {usingDemo ? ` · ${t('demoBadge')}` : ''}
          </p>
        </div>
        <div className="crm-g2-toolbar__actions">
          <Link href={'/dashboard/leads' as Route} className="ih-btn ih-btn--secondary">
            {t('openLegacy')}
          </Link>
        </div>
      </header>

      <CrmAnalyticsStrip
        compact
        contactCount={sorted.length}
        activityCount={sorted.filter((l) => l.status !== 'New').length}
        pipelineValue={formatBudget(
          String(
            sorted.reduce((sum, l) => sum + (Number(l.estimated_budget) || 0), 0),
          ),
          locale,
        )}
        contactTrend={sorted.map((_, i) => Math.max(1, i + 3 + (i % 4)))}
        activityTrend={[3, 5, 4, 7, 6, 8, 9]}
      />

      <div className="crm-g2-filters">
        <input
          className="crm-g2-filters__search"
          type="search"
          value={filters.search ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          placeholder={t('searchPlaceholder')}
          aria-label={t('searchPlaceholder')}
        />
        <select
          className="crm-g2-filters__select"
          value={filters.status ?? ''}
          onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value as LeadStatus | '' }))}
          aria-label={t('columns.stage')}
        >
          <option value="">{t('allStages')}</option>
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <Button
          type="button"
          onClick={() => {
            setPage(1);
            setApplied({ ...filters });
          }}
        >
          {t('apply')}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => {
            const cleared = { search: '', status: '' as const };
            setFilters(cleared);
            setApplied(cleared);
            setPage(1);
          }}
        >
          {t('clear')}
        </Button>
      </div>

      <div className="crm-g2-saved" role="group" aria-label={t('savedViews')}>
        {SAVED_VIEWS.map((view) => (
          <button
            key={view.id}
            type="button"
            className={`crm-g2-chip${(applied.status || '') === (view.status || '') ? ' crm-g2-chip--active' : ''}`}
            onClick={() => {
              const next = { ...applied, status: view.status, search: applied.search };
              setFilters(next);
              setApplied(next);
              setPage(1);
            }}
          >
            {t(`views.${view.id}` as 'views.all')}
          </button>
        ))}
      </div>

      {selectedIds.length > 0 ? (
        <div className="crm-g2-bulk">
          <span>{t('bulkSelected', { count: selectedIds.length })}</span>
          <Button type="button" variant="ghost" onClick={() => setSelectedIds([])}>
            {t('bulkClear')}
          </Button>
        </div>
      ) : null}

      {pageRows.length === 0 ? (
        <EmptyState title={t('empty')} description={t('emptyHint')} />
      ) : (
        <div className="crm-g2-table-wrap">
          <table className="crm-g2-table" data-testid="crm-g2-leads-table">
            <thead>
              <tr>
                <th className="crm-g2-table__check">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === pageRows.length && pageRows.length > 0}
                    onChange={toggleAll}
                    aria-label={t('selectAll')}
                  />
                </th>
                {(
                  [
                    ['full_name', 'name'],
                    ['company', 'company'],
                    ['status', 'stage'],
                    ['estimated_budget', 'budget'],
                    ['country', 'country'],
                    ['assigned_to', 'assigned'],
                    ['created_at', 'created'],
                    ['updated_at', 'lastActivity'],
                  ] as const
                ).map(([key, labelKey]) => (
                  <th key={key}>
                    <button type="button" className="crm-g2-table__sort" onClick={() => toggleSort(key)}>
                      {t(`columns.${labelKey}` as 'columns.name')}
                      {sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                    </button>
                  </th>
                ))}
                <th>{t('columns.priority')}</th>
                <th>{t('columns.investor')}</th>
                <th className="crm-g2-table__actions">{t('columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((lead) => {
                const priority = priorityFromScore(lead.cached_lead_score);
                return (
                  <tr
                    key={lead.id}
                    className={selectedIds.includes(lead.id) ? 'crm-g2-table__row--selected' : undefined}
                    onClick={() => setDrawerLead(lead)}
                  >
                    <td className="crm-g2-table__check" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(lead.id)}
                        onChange={() => toggleSelect(lead.id)}
                        aria-label={lead.full_name}
                      />
                    </td>
                    <td>
                      <strong>{lead.full_name}</strong>
                    </td>
                    <td>{lead.company ?? '—'}</td>
                    <td>
                      <StatusChip tone="default">{getStatusLabel(lead.status)}</StatusChip>
                    </td>
                    <td>{formatBudget(lead.estimated_budget, locale)}</td>
                    <td>{lead.country ?? '—'}</td>
                    <td>{lead.assigned_to ?? '—'}</td>
                    <td>{formatDate(lead.created_at, locale)}</td>
                    <td>{formatDate(lead.updated_at, locale)}</td>
                    <td>
                      <StatusChip
                        tone={priority === 'urgent' || priority === 'high' ? 'warning' : 'default'}
                      >
                        {t(`priority.${priority}` as 'priority.normal')}
                      </StatusChip>
                    </td>
                    <td>{lead.preferred_market ?? '—'}</td>
                    <td className="crm-g2-table__actions" onClick={(e) => e.stopPropagation()}>
                      <Link
                        href={`/dashboard/leads/${lead.id}` as Route}
                        className="crm-g2-link"
                      >
                        {t('open')}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="crm-g2-pagination">
        <Button
          type="button"
          variant="secondary"
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          {t('prev')}
        </Button>
        <span>
          {t('pageOf', { page, pages: pageCount })}
        </span>
        <Button
          type="button"
          variant="secondary"
          disabled={page >= pageCount}
          onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
        >
          {t('next')}
        </Button>
      </div>

      <CrmRecordDrawer
        open={Boolean(drawerLead)}
        onClose={() => setDrawerLead(null)}
        title={drawerLead?.full_name ?? ''}
        subtitle={drawerLead?.company ?? drawerLead?.email ?? undefined}
        badge={
          drawerLead ? (
            <StatusChip tone="default">{getStatusLabel(drawerLead.status)}</StatusChip>
          ) : null
        }
        summary={
          drawerLead ? (
            <dl className="crm-g2-drawer__grid">
              <CrmDrawerField label={t('columns.company')} value={drawerLead.company} />
              <CrmDrawerField label={t('columns.budget')} value={formatBudget(drawerLead.estimated_budget, locale)} />
              <CrmDrawerField label={t('columns.country')} value={drawerLead.country} />
              <CrmDrawerField label={t('columns.assigned')} value={drawerLead.assigned_to} />
              <CrmDrawerField label={t('columns.stage')} value={getStatusLabel(drawerLead.status)} />
              <CrmDrawerField label={tDrawer('notes')} value={drawerLead.notes} />
            </dl>
          ) : null
        }
        sections={{
          notes: drawerLead?.notes ? <p>{drawerLead.notes}</p> : <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
          activities: (
            <p className="crm-g2-drawer__empty">{t('lastTouch', { date: drawerLead ? formatDate(drawerLead.updated_at, locale) : '—' })}</p>
          ),
          ai: (
            <p className="crm-g2-drawer__empty">
              {t('aiHint', { score: drawerLead?.cached_lead_score ?? '—' })}
            </p>
          ),
          projects: (
            <p className="crm-g2-drawer__empty">{drawerLead?.interested_project ?? tDrawer('emptySection')}</p>
          ),
        }}
        footer={
          drawerLead && !drawerLead.id.startsWith('demo-') ? (
            <Link href={`/dashboard/leads/${drawerLead.id}` as Route} className="ih-btn">
              {t('openFull')}
            </Link>
          ) : null
        }
      />
    </div>
  );
}
