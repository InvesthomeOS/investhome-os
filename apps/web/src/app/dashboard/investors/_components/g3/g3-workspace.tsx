'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  archiveInvestor,
  createInvestor,
  fetchInvestor,
  fetchInvestorStats,
  fetchInvestors,
  formatCurrency,
  type Investor,
  type InvestorFilters,
  type InvestorInput,
  type InvestorStats,
  updateInvestor,
} from '@/lib/api/investors';
import { useInvestorLabels } from '@/lib/i18n/investor-labels';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';

import { InvestorFormModal } from '../investor-form-modal';
import { AnalyticsStrip } from './analytics-strip';
import { appendStageHistory, getBoardMeta, type InvestorPriority } from './board-meta';
import {
  ActivityPanel,
  ClosingsPanel,
  ContractsPanel,
  OpportunitiesPanel,
  PaymentsPanel,
  PortfolioPanel,
  ReservationsPanel,
} from './domain-panels';
import {
  INVESTOR_VIEWS,
  investorCapacity,
  lifecycleAsStatus,
  parseView,
  stageProbability,
  toLifecycleStage,
  type InvestorLifecycleStage,
  type InvestorViewId,
} from './lifecycle';
import { ListView, type ListColumnId } from './list-view';
import { OpsDrawer } from './ops-drawer';
import { PipelineBoard } from './pipeline-board';
import { deleteSavedView, listSavedViews, saveView, type InvestorSavedView } from './saved-views';

import './investors-g3.css';

type FormMode = 'create' | 'edit' | null;

const PAGE_SIZE = 100;

const EMPTY_FILTERS: InvestorFilters = {
  search: '',
  status: '',
  investor_type: '',
  country: '',
  preferred_investment_model: '',
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

export function InvestorsG3Workspace() {
  const t = useTranslations('investors');
  const tG3 = useTranslations('investors.g3');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const {
    getTypeLabel,
    getStatusLabel,
    getModelLabel,
    getAccreditationLabel,
    getRiskLabel,
    typeOptions,
    statusOptions,
    modelOptions,
  } = useInvestorLabels();

  const canView = user ? hasPermission(user, 'investors', 'view') : false;
  const canCreate = user ? hasPermission(user, 'investors', 'create') : false;
  const canUpdate = user ? hasPermission(user, 'investors', 'update') : false;
  const canArchive = user ? hasPermission(user, 'investors', 'archive') : false;

  const view = parseView(searchParams.get('view'));

  const setView = (next: InvestorViewId) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'pipeline') params.delete('view');
    else params.set('view', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const [investors, setInvestors] = useState<Investor[]>([]);
  const [stats, setStats] = useState<InvestorStats | null>(null);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [filters, setFilters] = useState<InvestorFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<InvestorFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedInvestor, setSelectedInvestor] = useState<Investor | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overStage, setOverStage] = useState<InvestorLifecycleStage | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [metaVersion, setMetaVersion] = useState(0);
  const [savedViews, setSavedViews] = useState<InvestorSavedView[]>([]);
  const [viewName, setViewName] = useState('');

  const stageLabel = useCallback(
    (stage: InvestorLifecycleStage) => tG3(`stages.${stage}`),
    [tG3],
  );

  const priorityLabel = useCallback(
    (p: InvestorPriority) => tG3(`priority.${p}`),
    [tG3],
  );

  const bumpMeta = () => setMetaVersion((v) => v + 1);

  const loadStats = useCallback(async () => {
    try {
      setStats(await fetchInvestorStats());
    } catch {
      setStats(null);
    }
  }, []);

  const loadInvestors = useCallback(
    async (nextFilters: InvestorFilters) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchInvestors(nextFilters);
        setInvestors(response.items);
        setTotal(response.total);
        setPages(response.pages);
      } catch {
        setError(t('loadError'));
        setInvestors([]);
        setTotal(0);
        setPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void loadStats();
    setSavedViews(listSavedViews());
  }, [loadStats]);

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    void loadInvestors(appliedFilters);
  }, [appliedFilters, loadInvestors, canView]);

  const handleOpenInvestor = useCallback((investor: Investor) => setSelectedInvestor(investor), []);
  useRecordDeepLink(fetchInvestor, handleOpenInvestor);

  const demoCount = useMemo(
    () => investors.filter((investor) => investor.is_demo).length,
    [investors],
  );

  const pipelineTotals = useMemo(() => {
    void metaVersion;
    const capacity = investors.reduce((s, i) => s + investorCapacity(i), 0);
    const weighted = investors.reduce((s, i) => {
      const stage = toLifecycleStage(i.status);
      if (stage === 'lost') return s;
      const meta = getBoardMeta(i.id);
      const p = meta.probability ?? stageProbability(stage);
      return s + (investorCapacity(i) * p) / 100;
    }, 0);
    return { capacity, weighted };
    // metaVersion intentionally invalidates weighted totals after local board-meta edits
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [investors, metaVersion]);

  const moveStage = async (id: string, stage: InvestorLifecycleStage) => {
    const investor = investors.find((i) => i.id === id);
    if (!investor) return;
    const current = toLifecycleStage(investor.status);
    if (current === stage) return;
    if (!canUpdate) {
      setToast(tG3('noStagePermission'));
      return;
    }

    const prev = investors;
    setInvestors((cur) =>
      cur.map((i) => (i.id === id ? { ...i, status: lifecycleAsStatus(stage) } : i)),
    );
    appendStageHistory(id, {
      from: current,
      to: stage,
      at: new Date().toISOString(),
    });
    bumpMeta();

    try {
      const updated = await updateInvestor(id, { status: lifecycleAsStatus(stage) });
      setInvestors((cur) => cur.map((i) => (i.id === id ? updated : i)));
      if (selectedInvestor?.id === id) setSelectedInvestor(updated);
      void loadStats();
    } catch {
      setInvestors(prev);
      setToast(tG3('stageError'));
    }
  };

  const handleSubmitInvestor = async (input: InvestorInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (formMode === 'create') {
        await createInvestor(input);
      } else if (formMode === 'edit' && selectedInvestor) {
        await updateInvestor(selectedInvestor.id, input);
      }
      setFormMode(null);
      await Promise.all([loadInvestors(appliedFilters), loadStats()]);
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveInvestor = async (investor: Investor) => {
    if (!canArchive) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await archiveInvestor(investor.id);
      setSelectedInvestor(null);
      await Promise.all([loadInvestors(appliedFilters), loadStats()]);
    } catch {
      setActionError(t('archiveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const panelLabels = useMemo(() => {
    const keys = [
      'opportunitiesTitle',
      'opportunitiesHint',
      'emptyOpportunities',
      'reservationsTitle',
      'reservationsHint',
      'emptyReservations',
      'contractsTitle',
      'contractsHint',
      'emptyContracts',
      'paymentsTitle',
      'paymentsHint',
      'emptyPayments',
      'commitments',
      'obligations',
      'closingsTitle',
      'closingsHint',
      'emptyClosings',
      'portfolioTitle',
      'portfolioHint',
      'portfolioGap',
      'emptyPortfolio',
      'demoOnly',
      'activityTitle',
      'activityHint',
      'emptyActivity',
      'colOpportunity',
      'colStage',
      'colValue',
      'colProbability',
      'colClose',
      'colReservation',
      'colStatus',
      'colInvestor',
      'colExpires',
      'colProject',
      'colDue',
      'colCapacity',
      'colProjects',
      'colNav',
      'data_live',
      'data_partial',
      'data_demo',
      'data_blocked',
      'loadError',
    ] as const;
    const out: Record<string, string> = {};
    for (const k of keys) out[k] = tG3(k);
    return out;
  }, [tG3]);

  const drawerLabels = useMemo(
    () => ({
      detailEyebrow: t('detailEyebrow'),
      demo: tCommon('demoData'),
      close: tCommon('close'),
      edit: tCommon('edit'),
      save: t('saveChanges'),
      saving: t('saving'),
      archive: t('archiveInvestor'),
      archiving: t('archiving'),
      email: t('detail.email'),
      phone: t('detail.phone'),
      country: t('detail.country'),
      capacity: t('detail.capacity'),
      stage: tG3('stage'),
      probability: tG3('probability'),
      assigned: t('detail.assignedTo'),
      expectedClose: tG3('expectedClose'),
      priority: tG3('priorityLabel'),
      nextAction: tG3('nextAction'),
      quickFields: tG3('quickFields'),
      probabilityGap: tG3('probabilityGap'),
      type: t('detail.type'),
      accreditation: t('detail.accreditation'),
      model: t('detail.model'),
      risk: t('detail.riskProfile'),
      markets: t('detail.markets'),
      projects: t('detail.projects'),
      source: t('detail.source'),
      statusLegacy: t('detail.status'),
      minTicket: t('detail.minimumTicket'),
      maxTicket: t('detail.maximumTicket'),
      created: t('detail.created'),
      updated: t('detail.updated'),
      unsupported: tG3('unsupported'),
      unsupportedFields: tG3('unsupportedFields'),
      stageNote: tG3('stageNote'),
      applyStage: tG3('applyStage'),
      stageHistory: tG3('stageHistory'),
      noHistory: tG3('noHistory'),
      notes: t('detail.notes'),
      tabOverview: tG3('tabs.overview'),
      tabProfile: tG3('tabs.profile'),
      tabStage: tG3('tabs.stage'),
      tabNotes: tG3('tabs.notes'),
      tabActivity: tG3('tabs.activity'),
      tabDocuments: tG3('tabs.documents'),
      tabAi: tG3('tabs.ai'),
      aiHint: tG3('aiHint'),
    }),
    [t, tG3, tCommon],
  );

  const columnLabels: Record<ListColumnId, string> = {
    select: tG3('colSelect'),
    name: t('table.name'),
    country: t('table.country'),
    type: t('table.type'),
    stage: tG3('stage'),
    capacity: t('table.capacity'),
    model: t('table.model'),
    assigned: t('table.assignedTo'),
    probability: tG3('probability'),
    lastContact: t('table.lastContact'),
    nextFollowUp: t('table.nextFollowUp'),
    updated: tG3('colUpdated'),
  };

  if (!user) {
    return (
      <main className="inv-g3">
        <div className="inv-g3__empty">{tCommon('loading')}</div>
      </main>
    );
  }

  if (!canView) {
    return (
      <main className="inv-g3">
        <div className="inv-g3__empty">{tG3('accessDenied')}</div>
      </main>
    );
  }

  return (
    <main className="inv-g3" data-testid="inv-g3-workspace">
      <header className="inv-g3__top">
        <div>
          <p className="inv-g3__eyebrow">{t('eyebrow')}</p>
          <h1 className="inv-g3__title">{tG3('title')}</h1>
          <p className="inv-g3__subtitle">
            {tG3('subtitle', {
              count: total,
              pipeline: formatCurrency(String(pipelineTotals.capacity), locale),
              weighted: formatCurrency(String(Math.round(pipelineTotals.weighted)), locale),
            })}
          </p>
        </div>
        <div className="inv-g3__top-actions">
          {canCreate ? (
            <button
              type="button"
              className="inv-g3__btn inv-g3__btn--primary"
              onClick={() => {
                setActionError(null);
                setFormMode('create');
              }}
            >
              {t('addInvestor')}
            </button>
          ) : null}
        </div>
      </header>

      <nav className="inv-g3__nav" aria-label={tG3('viewsLabel')}>
        {INVESTOR_VIEWS.map((v) => (
          <button
            key={v}
            type="button"
            className={`inv-g3__nav-btn${view === v ? ' is-active' : ''}`}
            onClick={() => setView(v)}
            data-testid={`inv-g3-nav-${v}`}
          >
            {tG3(`views.${v}`)}
          </button>
        ))}
      </nav>

      <div className="inv-g3__body">
        <ContextualAiActions module="investor" />

        {(view === 'pipeline' || view === 'list' || view === 'analytics') && (
          <AnalyticsStrip
            investors={investors}
            locale={locale}
            stageLabel={stageLabel}
            metaVersion={metaVersion}
            compact={view !== 'analytics'}
            labels={{
              total: t('stats.total'),
              active: t('stats.active'),
              pipeline: tG3('kpiPipeline'),
              weighted: tG3('kpiWeighted'),
              capacity: t('stats.capacity'),
              portfolio: tG3('kpiPortfolio'),
              stageDist: tG3('chartStageDist'),
              pipelineTrend: tG3('chartPipelineTrend'),
              conversion: tG3('chartConversion'),
            }}
          />
        )}

        {demoCount > 0 && (view === 'pipeline' || view === 'list') ? (
          <div className="inv-g3__banner" role="status">
            {t('demoBanner', { count: demoCount })}
          </div>
        ) : null}

        {(view === 'pipeline' || view === 'list') && (
          <>
            <div className="inv-g3__filters">
              <label>
                {t('searchLabel')}
                <input
                  value={filters.search ?? ''}
                  onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
                  placeholder={t('searchPlaceholder')}
                />
              </label>
              <label>
                {t('statusLabel')}
                <select
                  value={filters.status ?? ''}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      status: e.target.value as InvestorFilters['status'],
                    }))
                  }
                >
                  <option value="">{t('allStatuses')}</option>
                  {statusOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('typeLabel')}
                <select
                  value={filters.investor_type ?? ''}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      investor_type: e.target.value as InvestorFilters['investor_type'],
                    }))
                  }
                >
                  <option value="">{t('allTypes')}</option>
                  {typeOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                {t('countryLabel')}
                <input
                  value={filters.country ?? ''}
                  onChange={(e) => setFilters((f) => ({ ...f, country: e.target.value }))}
                  placeholder={t('countryPlaceholder')}
                />
              </label>
              <label>
                {t('modelLabel')}
                <select
                  value={filters.preferred_investment_model ?? ''}
                  onChange={(e) =>
                    setFilters((f) => ({
                      ...f,
                      preferred_investment_model: e.target
                        .value as InvestorFilters['preferred_investment_model'],
                    }))
                  }
                >
                  <option value="">{t('allModels')}</option>
                  {modelOptions.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'end' }}>
                <button
                  type="button"
                  className="inv-g3__btn inv-g3__btn--primary"
                  onClick={() => setAppliedFilters({ ...filters, page: 1 })}
                >
                  {tCommon('apply')}
                </button>
                <button
                  type="button"
                  className="inv-g3__btn"
                  onClick={() => {
                    setFilters(EMPTY_FILTERS);
                    setAppliedFilters(EMPTY_FILTERS);
                  }}
                >
                  {tCommon('reset')}
                </button>
              </div>
            </div>

            <div className="inv-g3__toolbar">
              <div className="inv-g3__toolbar-left">
                <div className="inv-g3__seg" role="group" aria-label={tG3('viewMode')}>
                  <button
                    type="button"
                    className={view === 'pipeline' ? 'is-active' : undefined}
                    onClick={() => setView('pipeline')}
                  >
                    {tG3('views.pipeline')}
                  </button>
                  <button
                    type="button"
                    className={view === 'list' ? 'is-active' : undefined}
                    onClick={() => setView('list')}
                  >
                    {tG3('views.list')}
                  </button>
                </div>
                {selectedIds.size > 0 ? (
                  <span className="inv-g3__chip is-active">
                    {tG3('selectedCount', { count: selectedIds.size })}
                  </span>
                ) : null}
              </div>
              <div className="inv-g3__toolbar-right">
                <input
                  value={viewName}
                  onChange={(e) => setViewName(e.target.value)}
                  placeholder={tG3('saveViewPlaceholder')}
                  style={{
                    border: '1px solid var(--inv-border)',
                    borderRadius: 6,
                    padding: '0.3rem 0.5rem',
                    fontSize: '0.72rem',
                  }}
                />
                <button
                  type="button"
                  className="inv-g3__btn"
                  onClick={() => {
                    if (!viewName.trim()) return;
                    const saved = saveView({
                      name: viewName.trim(),
                      scope: 'personal',
                      filters: {
                        search: appliedFilters.search,
                        status: appliedFilters.status || undefined,
                        investor_type: appliedFilters.investor_type || undefined,
                        country: appliedFilters.country,
                        preferred_investment_model:
                          appliedFilters.preferred_investment_model || undefined,
                        sort_by: appliedFilters.sort_by,
                        sort_order: appliedFilters.sort_order,
                      },
                    });
                    setSavedViews(listSavedViews());
                    setViewName('');
                    setToast(tG3('viewSaved', { name: saved.name }));
                  }}
                >
                  {tG3('saveView')}
                </button>
                {savedViews.slice(0, 3).map((sv) => (
                  <button
                    key={sv.id}
                    type="button"
                    className="inv-g3__chip"
                    onClick={() => {
                      const next: InvestorFilters = {
                        ...EMPTY_FILTERS,
                        search: sv.filters.search ?? '',
                        status: (sv.filters.status as InvestorFilters['status']) || '',
                        investor_type:
                          (sv.filters.investor_type as InvestorFilters['investor_type']) || '',
                        country: sv.filters.country ?? '',
                        preferred_investment_model:
                          (sv.filters.preferred_investment_model as InvestorFilters['preferred_investment_model']) ||
                          '',
                        sort_by: sv.filters.sort_by ?? 'updated_at',
                        sort_order: sv.filters.sort_order ?? 'desc',
                        page: 1,
                        page_size: PAGE_SIZE,
                      };
                      setFilters(next);
                      setAppliedFilters(next);
                    }}
                    onContextMenu={(e) => {
                      e.preventDefault();
                      deleteSavedView(sv.id);
                      setSavedViews(listSavedViews());
                    }}
                    title={tG3('savedViewHint')}
                  >
                    {sv.name}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {toast ? (
          <div className="inv-g3__toast" role="status">
            {toast}
            <button type="button" className="inv-g3__btn inv-g3__btn--ghost" onClick={() => setToast(null)}>
              ×
            </button>
          </div>
        ) : null}

        {actionError ? <div className="inv-g3__banner">{actionError}</div> : null}
        {error ? <div className="inv-g3__banner">{error}</div> : null}

        {loading ? <div className="inv-g3__empty">{t('loading')}</div> : null}

        {!loading && view === 'pipeline' ? (
          <PipelineBoard
            investors={investors}
            locale={locale}
            stageLabel={stageLabel}
            typeLabel={getTypeLabel}
            priorityLabel={priorityLabel}
            canMove={canUpdate}
            draggingId={draggingId}
            overStage={overStage}
            onDragStart={setDraggingId}
            onDragEnd={() => {
              setDraggingId(null);
              setOverStage(null);
            }}
            onDragOver={setOverStage}
            onDrop={(stage) => {
              if (draggingId) void moveStage(draggingId, stage);
              setDraggingId(null);
              setOverStage(null);
            }}
            onOpen={handleOpenInvestor}
            metaVersion={metaVersion}
          />
        ) : null}

        {!loading && view === 'list' ? (
          <>
            <ListView
              investors={investors}
              locale={locale}
              selectedIds={selectedIds}
              onToggleSelect={(id) => {
                setSelectedIds((prev) => {
                  const next = new Set(prev);
                  if (next.has(id)) next.delete(id);
                  else next.add(id);
                  return next;
                });
              }}
              onToggleSelectAll={() => {
                if (investors.every((i) => selectedIds.has(i.id))) {
                  setSelectedIds(new Set());
                } else {
                  setSelectedIds(new Set(investors.map((i) => i.id)));
                }
              }}
              onOpen={handleOpenInvestor}
              onSort={(sortBy) => {
                const sort_order: 'asc' | 'desc' =
                  appliedFilters.sort_by === sortBy && appliedFilters.sort_order === 'desc'
                    ? 'asc'
                    : 'desc';
                const next: InvestorFilters = {
                  ...appliedFilters,
                  sort_by: sortBy,
                  sort_order,
                  page: 1,
                };
                setFilters(next);
                setAppliedFilters(next);
              }}
              sortBy={appliedFilters.sort_by}
              sortOrder={appliedFilters.sort_order}
              stageLabel={stageLabel}
              typeLabel={getTypeLabel}
              columnLabels={columnLabels}
              metaVersion={metaVersion}
              onInlineAssign={
                canUpdate
                  ? async (investor, value) => {
                      try {
                        const updated = await updateInvestor(investor.id, {
                          assigned_to: value || null,
                        });
                        setInvestors((cur) =>
                          cur.map((i) => (i.id === investor.id ? updated : i)),
                        );
                      } catch {
                        setToast(t('saveError'));
                      }
                    }
                  : undefined
              }
            />
            <div className="inv-g3__pagination">
              <span>
                {t('pagination', {
                  page: appliedFilters.page ?? 1,
                  pages: pages || 1,
                  total,
                })}
              </span>
              <div style={{ display: 'flex', gap: '0.35rem' }}>
                <button
                  type="button"
                  className="inv-g3__btn"
                  disabled={(appliedFilters.page ?? 1) <= 1}
                  onClick={() =>
                    setAppliedFilters((c) => ({ ...c, page: Math.max(1, (c.page ?? 1) - 1) }))
                  }
                >
                  {t('prevPage')}
                </button>
                <button
                  type="button"
                  className="inv-g3__btn"
                  disabled={(appliedFilters.page ?? 1) >= pages}
                  onClick={() =>
                    setAppliedFilters((c) => ({ ...c, page: (c.page ?? 1) + 1 }))
                  }
                >
                  {t('nextPage')}
                </button>
              </div>
            </div>
          </>
        ) : null}

        {!loading && view === 'opportunities' ? (
          <OpportunitiesPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}
        {!loading && view === 'reservations' ? (
          <ReservationsPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}
        {!loading && view === 'contracts' ? (
          <ContractsPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}
        {!loading && view === 'payments' ? (
          <PaymentsPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}
        {!loading && view === 'closings' ? (
          <ClosingsPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}
        {!loading && view === 'portfolio' ? (
          <PortfolioPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}
        {!loading && view === 'activity' ? (
          <ActivityPanel
            locale={locale}
            investors={investors}
            labels={panelLabels}
            stageLabel={stageLabel}
          />
        ) : null}

        {stats && view === 'analytics' ? (
          <p className="inv-g3__subtitle">
            {t('stats.invested')}: {stats.invested} · {t('stats.capacity')}:{' '}
            {formatCurrency(stats.total_investment_capacity, locale)}
          </p>
        ) : null}
      </div>

      <OpsDrawer
        investor={selectedInvestor}
        locale={locale}
        canUpdate={canUpdate}
        archiving={submitting}
        saving={submitting}
        stageLabel={stageLabel}
        typeLabel={getTypeLabel}
        statusLabel={getStatusLabel}
        modelLabel={getModelLabel}
        accreditationLabel={getAccreditationLabel}
        riskLabel={getRiskLabel}
        priorityLabel={priorityLabel}
        labels={drawerLabels}
        onClose={() => setSelectedInvestor(null)}
        onEdit={(inv) => {
          setSelectedInvestor(inv);
          setFormMode('edit');
        }}
        onArchive={handleArchiveInvestor}
        onStageChange={async (inv, stage, note) => {
          if (note) {
            appendStageHistory(inv.id, {
              from: toLifecycleStage(inv.status),
              to: stage,
              at: new Date().toISOString(),
              note,
            });
            bumpMeta();
          }
          await moveStage(inv.id, stage);
        }}
        onFieldPatch={async (inv, patch) => {
          setSubmitting(true);
          try {
            const updated = await updateInvestor(inv.id, patch);
            setInvestors((cur) => cur.map((i) => (i.id === inv.id ? updated : i)));
            setSelectedInvestor(updated);
          } catch {
            setToast(t('saveError'));
          } finally {
            setSubmitting(false);
          }
        }}
        metaVersion={metaVersion}
        onMetaChange={bumpMeta}
      />

      {formMode ? (
        <InvestorFormModal
          mode={formMode}
          investor={formMode === 'edit' ? selectedInvestor : null}
          submitting={submitting}
          error={actionError}
          onClose={() => setFormMode(null)}
          onSubmit={handleSubmitInvestor}
        />
      ) : null}
    </main>
  );
}
