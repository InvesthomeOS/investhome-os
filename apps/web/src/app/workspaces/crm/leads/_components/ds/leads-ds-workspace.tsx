'use client';

import type { Route } from 'next';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import {
  Button,
  EmptyState,
  Input,
  KpiCard,
  SegmentedControl,
  Select,
  StatusChip,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAuth } from '@/lib/auth/auth-context';
import { hasPermission } from '@/lib/api/auth';
import {
  createLead,
  fetchLeads,
  formatBudget,
  type Lead,
  type LeadInput,
  type LeadStatus,
} from '@/lib/api/leads';
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { LeadFormModal } from '@/app/dashboard/leads/_components/lead-form-modal';

import {
  avatarTone,
  DEMO_LEADS,
  deriveLeadsKpis,
  EMPTY_LEADS_FILTERS,
  filterLeads,
  formatDisplayDate,
  formatRelativeActivity,
  initials,
  LEAD_QUICK_FILTERS,
  LEADS_KPI_ICONS,
  leadStatusTone,
  scoreBand,
  type LeadQuickFilter,
  type LeadScoreFilter,
  type LeadSortKey,
  type LeadsDsFilters,
  type LeadsKpiKey,
} from './leads-ds-model';

import './leads-ds.css';

const PAGE_SIZE = 10;
const FILTER_KEY = 'investhome.crm.leads.ds.filters';

function LeadAvatar({
  name,
  size = 'sm',
}: {
  name: string;
  size?: 'sm' | 'lg';
}) {
  return (
    <span
      className={`lds__avatar is-${avatarTone(name)}${size === 'lg' ? ' is-lg' : ''}`}
      aria-hidden="true"
    >
      {initials(name)}
    </span>
  );
}

function ScoreCell({ score, tooltip }: { score: number | null; tooltip: string }) {
  const band = scoreBand(score);
  return (
    <span className="lds__score" title={tooltip}>
      {score ?? '—'}
      <span className={`lds__score-dot is-${band}`} aria-hidden="true" />
    </span>
  );
}

function RowActions({
  lead,
  onOpen,
  onCall,
  onEmail,
  onWhatsApp,
  onTask,
}: {
  lead: Lead;
  onOpen: () => void;
  onCall: () => void;
  onEmail: () => void;
  onWhatsApp: () => void;
  onTask: () => void;
}) {
  const t = useTranslations('crm.leads.ds');

  return (
    <div className="lds__actions" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className="lds__icon-btn"
        aria-label={t('actions.call')}
        title={t('actions.call')}
        onClick={onCall}
        disabled={!lead.phone}
      >
        <IhIcon name="meeting" size={13} />
      </button>
      <button
        type="button"
        className="lds__icon-btn"
        aria-label={t('actions.email')}
        title={t('actions.email')}
        onClick={onEmail}
        disabled={!lead.email}
      >
        <IhIcon name="inbox" size={13} />
      </button>
      <button
        type="button"
        className="lds__icon-btn"
        aria-label={t('actions.whatsapp')}
        title={t('actions.whatsapp')}
        onClick={onWhatsApp}
        disabled={!lead.phone}
      >
        <IhIcon name="check" size={13} />
      </button>
      <button
        type="button"
        className="lds__icon-btn"
        aria-label={t('actions.createTask')}
        title={t('actions.createTask')}
        onClick={onTask}
      >
        <IhIcon name="plus" size={13} />
      </button>
      <button
        type="button"
        className="lds__icon-btn"
        aria-label={t('actions.openDetail')}
        title={t('actions.openDetail')}
        onClick={onOpen}
      >
        <IhIcon name="arrowRight" size={13} />
      </button>
    </div>
  );
}

function PreviewPanel({
  lead,
  onClose,
  onOpenDetail,
  variant = 'side',
}: {
  lead: Lead | null;
  onClose: () => void;
  onOpenDetail: (lead: Lead) => void;
  variant?: 'side' | 'drawer';
}) {
  const t = useTranslations('crm.leads.ds');
  const locale = useLocale();
  const router = useRouter();
  const { getStatusLabel, getSourceLabel } = useLeadLabels();
  const previewClass =
    variant === 'side' ? 'lds__preview lds__preview--side' : 'lds__preview';

  if (!lead) {
    return (
      <aside className={previewClass} aria-label={t('preview.aria')}>
        <div className="lds__preview-placeholder">
          <strong>{t('preview.emptyTitle')}</strong>
          <p>{t('preview.emptyHint')}</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className={previewClass} aria-label={t('preview.aria')}>
      <div className="lds__preview-head">
        <div className="lds__preview-identity">
          <LeadAvatar name={lead.full_name} size="lg" />
          <div className="lds__preview-identity-text">
            <strong title={lead.full_name}>{lead.full_name}</strong>
            <div className="lds__preview-meta">
              <StatusChip tone={leadStatusTone(lead.status)}>
                {getStatusLabel(lead.status)}
              </StatusChip>
              <ScoreCell score={lead.cached_lead_score} tooltip={t('score.tooltip')} />
            </div>
          </div>
        </div>
        <div className="lds__preview-tools">
          <button
            type="button"
            className="lds__icon-btn"
            aria-label={t('actions.openDetail')}
            title={t('actions.openDetail')}
            onClick={() => onOpenDetail(lead)}
          >
            <IhIcon name="arrowRight" size={13} />
          </button>
          <button
            type="button"
            className="lds__icon-btn"
            aria-label={t('preview.close')}
            title={t('preview.close')}
            onClick={onClose}
          >
            ×
          </button>
        </div>
      </div>

      <div className="lds__preview-body">
        <section className="lds__preview-section">
          <h3>{t('preview.info')}</h3>
          <div className="lds__preview-card">
            <dl className="lds__kv">
              <dt>{t('columns.company')}</dt>
              <dd title={lead.company ?? undefined}>{lead.company ?? '—'}</dd>
              <dt>{t('preview.email')}</dt>
              <dd title={lead.email ?? undefined}>{lead.email ?? '—'}</dd>
              <dt>{t('preview.phone')}</dt>
              <dd title={lead.phone ?? undefined}>{lead.phone ?? '—'}</dd>
              <dt>{t('preview.location')}</dt>
              <dd
                title={
                  [lead.preferred_market, lead.country].filter(Boolean).join(' · ') ||
                  undefined
                }
              >
                {[lead.preferred_market, lead.country].filter(Boolean).join(' · ') || '—'}
              </dd>
              <dt>{t('columns.source')}</dt>
              <dd>{getSourceLabel(lead.source)}</dd>
              <dt>{t('columns.created')}</dt>
              <dd>{formatDisplayDate(lead.created_at, locale)}</dd>
              <dt>{t('columns.score')}</dt>
              <dd>{lead.cached_lead_score ?? '—'}</dd>
            </dl>
          </div>
        </section>

        <section className="lds__preview-section">
          <h3>{t('preview.lastInteraction')}</h3>
          <div className="lds__preview-card">
            <div className="lds__preview-block">
              <span className="lds__preview-block-icon" aria-hidden="true">
                <IhIcon name="activity" size={14} />
              </span>
              <div>
                <strong>{t('preview.lastTouchLabel')}</strong>
                <span>
                  {formatRelativeActivity(lead.updated_at, locale)}
                  {lead.assigned_to ? ` · ${lead.assigned_to}` : ''}
                </span>
                <button
                  type="button"
                  className="lds__preview-link"
                  onClick={() => onOpenDetail(lead)}
                >
                  {t('preview.viewDetails')}
                </button>
              </div>
            </div>
          </div>
        </section>

        <section className="lds__preview-section">
          <h3>{t('preview.nextStep')}</h3>
          <div className="lds__preview-card">
            {lead.status === 'Meeting Scheduled' || lead.interested_project ? (
              <div className="lds__preview-block">
                <span className="lds__preview-block-icon" aria-hidden="true">
                  <IhIcon name="calendar" size={14} />
                </span>
                <div>
                  <strong
                    title={
                      lead.interested_project
                        ? t('preview.projectFollowUp', { project: lead.interested_project })
                        : getStatusLabel(lead.status)
                    }
                  >
                    {lead.interested_project
                      ? t('preview.projectFollowUp', { project: lead.interested_project })
                      : getStatusLabel(lead.status)}
                  </strong>
                  <span title={lead.assigned_to ?? undefined}>
                    {lead.assigned_to
                      ? t('preview.assignee', { name: lead.assigned_to })
                      : t('preview.noAssignee')}
                  </span>
                  <button
                    type="button"
                    className="lds__preview-link"
                    onClick={() => router.push('/workspaces/crm/calendar' as Route)}
                  >
                    {t('preview.goCalendar')}
                  </button>
                  <button
                    type="button"
                    className="lds__preview-link"
                    onClick={() =>
                      router.push(`/workspaces/crm/tasks?lead=${lead.id}` as Route)
                    }
                  >
                    {t('preview.openTask')}
                  </button>
                </div>
              </div>
            ) : (
              <p className="lds__preview-empty">{t('preview.noNextStep')}</p>
            )}
          </div>
        </section>

        <section className="lds__preview-section">
          <h3>{t('preview.notes')}</h3>
          <div className="lds__preview-card">
            {lead.notes ? (
              <>
                <p className="lds__preview-note">{lead.notes}</p>
                <button
                  type="button"
                  className="lds__preview-link"
                  onClick={() => onOpenDetail(lead)}
                >
                  {t('preview.viewAllNotes')}
                </button>
              </>
            ) : (
              <p className="lds__preview-empty">{t('preview.noNotes')}</p>
            )}
          </div>
        </section>
      </div>
    </aside>
  );
}

function TableSkeleton() {
  return (
    <div className="lds__skeleton" aria-hidden="true">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="lds__skeleton-row" />
      ))}
    </div>
  );
}

function LeadsDsWorkspaceInner() {
  const t = useTranslations('crm.leads.ds');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const { user } = useAuth();
  const { getStatusLabel, getSourceLabel, statusOptions, sourceOptions } = useLeadLabels();

  const canView = user
    ? hasPermission(user, 'leads', 'view') || hasPermission(user, 'sales', 'view')
    : false;
  const canCreate = user
    ? hasPermission(user, 'leads', 'create') || hasPermission(user, 'sales', 'create')
    : false;

  const [leads, setLeads] = useState<Lead[]>([]);
  const [usingDemo, setUsingDemo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<LeadsDsFilters>(EMPTY_LEADS_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(FILTER_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as Partial<LeadsDsFilters>;
      setFilters((prev) => ({ ...prev, ...parsed, search: parsed.search ?? '' }));
      setSearchDraft(parsed.search ?? '');
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 1279px)');
    const sync = () => setNarrow(mq.matches);
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchLeads({});
      if (res.items.length === 0) {
        setLeads(DEMO_LEADS);
        setUsingDemo(true);
      } else {
        setLeads(res.items);
        setUsingDemo(false);
      }
    } catch {
      setLeads(DEMO_LEADS);
      setUsingDemo(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    if (!canView) {
      setLoading(false);
      return;
    }
    void load();
  }, [user, canView, load]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  useEffect(() => {
    try {
      localStorage.setItem(FILTER_KEY, JSON.stringify(filters));
    } catch {
      /* ignore */
    }
  }, [filters]);

  const owners = useMemo(() => {
    const set = new Set<string>();
    for (const row of leads) {
      if (row.assigned_to) set.add(row.assigned_to);
    }
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [leads]);

  const filtered = useMemo(() => filterLeads(leads, filters), [leads, filters]);

  const formatMoney = useCallback(
    (value: number) => {
      if (!value) return formatBudget(null, locale);
      return formatBudget(String(value), locale);
    },
    [locale],
  );

  const kpis = useMemo(() => deriveLeadsKpis(leads, formatMoney), [leads, formatMoney]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, pages);
  const pageItems = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);
  const rangeStart = filtered.length === 0 ? 0 : (pageSafe - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(pageSafe * PAGE_SIZE, filtered.length);

  const previewLead = useMemo(
    () => (previewId ? (leads.find((l) => l.id === previewId) ?? null) : null),
    [leads, previewId],
  );

  useEffect(() => {
    if (loading || filtered.length === 0) return;
    if (previewId && filtered.some((l) => l.id === previewId)) return;
    setPreviewId(filtered[0]!.id);
  }, [loading, previewId, filtered]);

  const patchFilters = (patch: Partial<LeadsDsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  };

  const openDetail = (lead: Lead) => {
    if (lead.id.startsWith('demo-')) return;
    router.push(`/dashboard/leads/${lead.id}` as Route);
  };

  const selectLead = (lead: Lead) => {
    setPreviewId(lead.id);
    if (narrow) setDrawerOpen(true);
  };

  const closePreview = () => {
    setPreviewId(null);
    setDrawerOpen(false);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  };

  const toggleAll = () => {
    if (selectedIds.length === pageItems.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(pageItems.map((r) => r.id));
    }
  };

  const handleCreate = async (input: LeadInput) => {
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      const created = await createLead(input);
      setCreateOpen(false);
      setUsingDemo(false);
      setLeads((prev) => [created, ...prev.filter((l) => !l.id.startsWith('demo-'))]);
      setPreviewId(created.id);
    } catch {
      setCreateError(t('createError'));
    } finally {
      setCreateSubmitting(false);
    }
  };

  if (!user) {
    return (
      <div className="lds" data-testid="leads-ds-workspace">
        <div className="lds__empty">{tCommon('loading')}</div>
      </div>
    );
  }

  if (!canView) {
    return (
      <div className="lds" data-testid="leads-ds-workspace">
        <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />
      </div>
    );
  }

  const emptyState = (
    <div className="lds__empty" data-testid="leads-ds-empty">
      <strong>{t('empty.title')}</strong>
      <p>{t('empty.description')}</p>
      <div className="lds__empty-actions">
        {canCreate ? (
          <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
            <IhIcon name="plus" size={13} />
            {t('empty.add')}
          </Button>
        ) : null}
      </div>
    </div>
  );

  return (
    <div className="lds" data-testid="leads-ds-workspace">
      <header className="lds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="lds__header-actions">
          {canCreate ? (
            <Button
              variant="primary"
              size="sm"
              onClick={() => setCreateOpen(true)}
              data-testid="leads-ds-add"
            >
              <IhIcon name="plus" size={13} />
              {t('actions.add')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="lds__kpi-row" aria-label={t('kpis.aria')}>
        {loading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="lds__kpi-skel" />
            ))
          : kpis.map((kpi) => (
              <KpiCard
                key={kpi.key}
                className={`lds__kpi${kpi.key === 'potentialValue' ? ' is-money' : ''}`}
                label={t(`kpis.${kpi.key}` as `kpis.${LeadsKpiKey}`)}
                value={kpi.value}
                hint={t(`kpis.hints.${kpi.key}` as `kpis.hints.${LeadsKpiKey}`)}
                delta={kpi.delta ? `${kpi.delta} ${t('kpis.vsLastMonth')}` : undefined}
                {...(kpi.deltaTone ? { deltaTone: kpi.deltaTone } : {})}
                icon={<IhIcon name={LEADS_KPI_ICONS[kpi.key]} size={18} />}
              />
            ))}
      </section>

      <section className="lds__toolbar" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={searchDraft}
          onChange={(e) => setSearchDraft(e.target.value)}
          placeholder={t('filters.searchPlaceholder')}
          data-testid="leads-ds-search"
        />
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) =>
            patchFilters({ status: e.target.value as LeadStatus | '' })
          }
        >
          <option value="">{t('filters.any')}</option>
          {statusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.source')}
          value={filters.source}
          onChange={(e) => patchFilters({ source: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {sourceOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={filters.owner}
          onChange={(e) => patchFilters({ owner: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {owners.map((owner) => (
            <option key={owner} value={owner}>
              {owner}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.score')}
          value={filters.score}
          onChange={(e) =>
            patchFilters({ score: e.target.value as LeadScoreFilter })
          }
        >
          <option value="">{t('filters.any')}</option>
          <option value="high">{t('score.high')}</option>
          <option value="medium">{t('score.medium')}</option>
          <option value="low">{t('score.low')}</option>
        </Select>
        <Select
          label={t('filters.sort')}
          value={filters.sort}
          onChange={(e) =>
            patchFilters({ sort: e.target.value as LeadSortKey })
          }
        >
          <option value="activity_desc">{t('sort.activity_desc')}</option>
          <option value="name_asc">{t('sort.name_asc')}</option>
          <option value="name_desc">{t('sort.name_desc')}</option>
          <option value="score_desc">{t('sort.score_desc')}</option>
          <option value="created_desc">{t('sort.created_desc')}</option>
          <option value="budget_desc">{t('sort.budget_desc')}</option>
        </Select>
      </section>

      <section className="lds__quick" aria-label={t('quick.aria')}>
        <SegmentedControl
          ariaLabel={t('quick.aria')}
          value={filters.quick}
          onChange={(next) => patchFilters({ quick: next as LeadQuickFilter })}
          options={LEAD_QUICK_FILTERS.map((key) => ({
            value: key,
            label: t(`quick.${key}`),
          }))}
        />
      </section>

      <div className={`lds__workspace${narrow ? ' is-no-preview' : ''}`}>
        <section className="lds__table-section" aria-label={t('table.aria')}>
          <div className="lds__main-toolbar">
            <h2>
              {t('table.title')}
              <span className="lds__count">{filtered.length}</span>
              {usingDemo ? (
                <span className="lds__demo-badge">{t('demoBadge')}</span>
              ) : null}
            </h2>
          </div>

          {loading ? (
            <TableSkeleton />
          ) : pageItems.length === 0 ? (
            emptyState
          ) : (
            <div className="lds__table-wrap">
              <table className="lds__table" data-testid="leads-ds-table">
                <colgroup>
                  <col className="col-check" />
                  <col className="col-lead" />
                  <col className="col-company" />
                  <col className="col-status" />
                  <col className="col-score" />
                  <col className="col-source" />
                  <col className="col-owner" />
                  <col className="col-activity" />
                  <col className="col-created" />
                  <col className="col-actions" />
                </colgroup>
                <thead>
                  <tr>
                    <th className="lds__check" scope="col">
                      <input
                        type="checkbox"
                        checked={
                          selectedIds.length === pageItems.length && pageItems.length > 0
                        }
                        onChange={toggleAll}
                        aria-label={t('selectAll')}
                      />
                    </th>
                    <th scope="col">{t('columns.lead')}</th>
                    <th scope="col">{t('columns.company')}</th>
                    <th scope="col">{t('columns.status')}</th>
                    <th scope="col">{t('columns.score')}</th>
                    <th scope="col">{t('columns.source')}</th>
                    <th scope="col">{t('columns.owner')}</th>
                    <th scope="col">{t('columns.lastActivity')}</th>
                    <th scope="col">{t('columns.created')}</th>
                    <th scope="col">{t('columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((lead) => {
                    const selected = previewId === lead.id;
                    const checked = selectedIds.includes(lead.id);
                    return (
                      <tr
                        key={lead.id}
                        className={`lds__row${selected ? ' is-selected' : ''}`}
                        data-testid={`leads-ds-row-${lead.id}`}
                        onClick={() => selectLead(lead)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            selectLead(lead);
                          }
                        }}
                        tabIndex={0}
                      >
                        <td
                          className="lds__check"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => toggleSelect(lead.id)}
                            aria-label={lead.full_name}
                          />
                        </td>
                        <td>
                          <div className="lds__lead-cell">
                            <LeadAvatar name={lead.full_name} />
                            <div className="lds__lead-meta">
                              <strong title={lead.full_name}>{lead.full_name}</strong>
                              <span title={lead.email ?? undefined}>
                                {lead.email ?? '—'}
                              </span>
                            </div>
                          </div>
                        </td>
                        <td title={lead.company ?? undefined}>{lead.company ?? '—'}</td>
                        <td>
                          <StatusChip tone={leadStatusTone(lead.status)}>
                            {getStatusLabel(lead.status)}
                          </StatusChip>
                        </td>
                        <td>
                          <ScoreCell
                            score={lead.cached_lead_score}
                            tooltip={t('score.tooltip')}
                          />
                        </td>
                        <td>{getSourceLabel(lead.source)}</td>
                        <td>
                          {lead.assigned_to ? (
                            <span className="lds__owner" title={lead.assigned_to}>
                              <span className="lds__owner-avatar" aria-hidden="true">
                                {initials(lead.assigned_to)}
                              </span>
                              <span>{lead.assigned_to}</span>
                            </span>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>{formatRelativeActivity(lead.updated_at, locale)}</td>
                        <td>{formatDisplayDate(lead.created_at, locale)}</td>
                        <td>
                          <RowActions
                            lead={lead}
                            onOpen={() => openDetail(lead)}
                            onCall={() => {
                              if (lead.phone) window.location.href = `tel:${lead.phone}`;
                            }}
                            onEmail={() => {
                              if (lead.email) {
                                window.location.href = `mailto:${lead.email}`;
                              }
                            }}
                            onWhatsApp={() => {
                              if (lead.phone) {
                                const digits = lead.phone.replace(/\D/g, '');
                                window.open(
                                  `https://wa.me/${digits}`,
                                  '_blank',
                                  'noopener,noreferrer',
                                );
                              }
                            }}
                            onTask={() => {
                              router.push(
                                `/workspaces/crm/tasks?lead=${lead.id}` as Route,
                              );
                            }}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {!loading && filtered.length > 0 ? (
            <div className="lds__pagination">
              <span>
                {t('pagination', {
                  start: rangeStart,
                  end: rangeEnd,
                  total: filtered.length,
                })}
              </span>
              <div>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={pageSafe <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  {t('prevPage')}
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={pageSafe >= pages}
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                >
                  {t('nextPage')}
                </Button>
              </div>
            </div>
          ) : null}
        </section>

        {!narrow ? (
          <PreviewPanel
            lead={previewLead}
            onClose={closePreview}
            onOpenDetail={openDetail}
          />
        ) : null}
      </div>

      {narrow ? (
        <div
          className={`lds__drawer-layer${drawerOpen && previewLead ? ' is-open' : ''}`}
          role="presentation"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) closePreview();
          }}
        >
          <div className="lds__drawer" role="dialog" aria-modal="true">
            <PreviewPanel
              lead={previewLead}
              onClose={closePreview}
              onOpenDetail={openDetail}
              variant="drawer"
            />
          </div>
        </div>
      ) : null}

      <LeadFormModal
        mode={createOpen ? 'create' : null}
        lead={null}
        submitting={createSubmitting}
        error={createError}
        onClose={() => {
          setCreateOpen(false);
          setCreateError(null);
        }}
        onSubmit={(input) => {
          void handleCreate(input);
        }}
      />
    </div>
  );
}

export function LeadsDsWorkspace() {
  const t = useTranslations('common');
  return (
    <Suspense
      fallback={
        <div className="lds">
          <div className="lds__empty">{t('loading')}</div>
        </div>
      }
    >
      <LeadsDsWorkspaceInner />
    </Suspense>
  );
}
