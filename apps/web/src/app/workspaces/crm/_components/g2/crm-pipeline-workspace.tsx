'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import {
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  LoadingState,
  PageHeader,
  Pagination,
  SearchInput,
  SegmentedControl,
  Select,
  StatusChip,
  Table,
  TableToolbar,
} from '@investhome/ui';

import { SalesFormModal } from '@/app/dashboard/sales/_components/sales-form-modal';
import { SalesNextActionModal } from '@/app/dashboard/sales/_components/sales-next-action-modal';
import { SalesStageChangeModal } from '@/app/dashboard/sales/_components/sales-stage-change-modal';
import { IhIcon } from '@/components/icons/ih-icons';
import { fetchUsers, type CurrentUser, type UserRecord } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import {
  archiveOpportunity,
  canTransitionStage,
  changeOpportunityProbability,
  changeOpportunityStage,
  createOpportunity,
  fetchOpportunities,
  fetchOpportunity,
  formatMoney,
  formatShortDate,
  restoreOpportunity,
  stageRequiresModal,
  updateOpportunityNextAction,
  type OpportunityLossReason,
  type OpportunityNextAction,
  type OpportunityPriority,
  type OpportunityStage,
  type SalesOpportunity,
  type SalesOpportunityInput,
} from '@/lib/api/sales';
import { useAuth } from '@/lib/auth/auth-context';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';
import { useSalesLabels } from '@/lib/i18n/sales-labels';
import {
  CRM_CONTACT_UPDATED_EVENT,
  opportunityContactId,
  useContactCard,
} from '@/workspaces/crm/contact-card/contact-card-context';

import { CrmDrawerField, CrmRecordDrawer } from './crm-record-drawer';
import { OpportunityCard } from './opportunity-card';
import {
  OpportunityDetailSections,
  type OpportunityDetailPreview,
} from './opportunity-detail-sections';
import {
  aggregateOpportunitySummary,
  DEFAULT_OPPORTUNITY_FILTERS,
  filterOpportunities,
  getOpportunityCardContext,
  getOpportunityPermissions,
  isOpportunityPriority,
  isOpportunityStage,
  isOpportunityOverdue,
  OPPORTUNITY_STAGE_ORDER,
  stageCurrencyTotals,
  type OpportunityCardContext,
  type OpportunityPermissions,
  type OpportunityWorkspaceFilters,
} from './opportunity-presentation';

const PAGE_SIZE = 20;
const MAX_LIVE_ITEMS = 200;
/** Default currency KPI surface — remaining currencies expand via “see all”. */
const DEFAULT_CURRENCY_KPI = ['USD', 'TRY'] as const;

function currencyGlyph(code: string) {
  if (code === 'USD') return '$';
  if (code === 'TRY') return '₺';
  if (code === 'EUR') return '€';
  if (code === 'GBP') return '£';
  return code.slice(0, 1).toUpperCase();
}

export type OpportunityPreviewState = 'ready' | 'loading' | 'error' | 'empty' | 'permission';

export type OpportunityWorkspacePreview = {
  sourceLabel: string;
  state: OpportunityPreviewState;
  items: SalesOpportunity[];
  users: UserRecord[];
  permissions: OpportunityPermissions;
  details?: OpportunityDetailPreview;
  /** Optional local-only customer/project labels for card hierarchy (preview fixtures). */
  cardContext?: Record<string, OpportunityCardContext>;
};

function readFilters(params: URLSearchParams): OpportunityWorkspaceFilters {
  const view = params.get('view');
  const direction = params.get('direction');
  const page = Number(params.get('page') ?? '1');
  return {
    ...DEFAULT_OPPORTUNITY_FILTERS,
    view: view === 'list' ? 'list' : 'board',
    search: params.get('q') ?? params.get('search') ?? '',
    stage: isOpportunityStage(params.get('stage')) ? params.get('stage') as OpportunityStage : '',
    assignee: params.get('assignee') ?? '',
    priority: isOpportunityPriority(params.get('priority'))
      ? params.get('priority') as OpportunityPriority
      : '',
    archived: params.get('archived') === 'true',
    sort: params.get('sort') ?? 'updated_at',
    direction: direction === 'asc' ? 'asc' : 'desc',
    page: Number.isFinite(page) && page > 0 ? Math.floor(page) : 1,
  };
}

function priorityTone(priority: SalesOpportunity['priority']) {
  if (priority === 'urgent') return 'danger' as const;
  if (priority === 'high') return 'warning' as const;
  return 'default' as const;
}

type OpportunityWorkspaceContentProps = {
  authLoading: boolean;
  user: CurrentUser | null;
  preview?: OpportunityWorkspacePreview;
};

export function CrmPipelineWorkspace({ preview }: { preview?: OpportunityWorkspacePreview }) {
  if (preview) {
    return <CrmPipelineWorkspaceContent authLoading={false} user={null} preview={preview} />;
  }
  return <CrmPipelineWorkspaceLive />;
}

function CrmPipelineWorkspaceLive() {
  const { user, loading: authLoading } = useAuth();
  return <CrmPipelineWorkspaceContent authLoading={authLoading} user={user} />;
}

function CrmPipelineWorkspaceContent({
  authLoading,
  user,
  preview,
}: OpportunityWorkspaceContentProps) {
  const t = useTranslations('crm.g2.pipeline');
  const tSales = useTranslations('sales');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getStageLabel, getPriorityLabel, getNextActionLabel } = useSalesLabels();
  const { openContact } = useContactCard();
  const permissions = useMemo(
    () => preview?.permissions ?? getOpportunityPermissions(user),
    [preview?.permissions, user],
  );
  const [narrowViewport, setNarrowViewport] = useState(false);
  const filters = useMemo(
    () => readFilters(new URLSearchParams(searchParams.toString())),
    [searchParams],
  );
  const effectiveView =
    filters.view === 'board' && (!permissions.canViewBoard || narrowViewport)
      ? 'list'
      : filters.view;

  const [items, setItems] = useState<SalesOpportunity[]>(
    preview?.state === 'ready' ? preview.items : [],
  );
  const [serverTotal, setServerTotal] = useState(
    preview?.state === 'ready' ? preview.items.length : 0,
  );
  const [loading, setLoading] = useState(preview?.state === 'loading' || !preview);
  const [error, setError] = useState<string | null>(
    preview?.state === 'error' ? 'Preview error state: opportunities are unavailable.' : null,
  );
  const [users, setUsers] = useState<UserRecord[]>(preview?.users ?? []);
  const [enrichmentWarning, setEnrichmentWarning] = useState(false);
  const [selected, setSelected] = useState<SalesOpportunity | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const draggingIdRef = useRef<string | null>(null);
  const [overStage, setOverStage] = useState<OpportunityStage | null>(null);
  const [announcement, setAnnouncement] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [stageModal, setStageModal] = useState<{
    opportunity: SalesOpportunity;
    targetStage: OpportunityStage | null;
  } | null>(null);
  const [nextActionModal, setNextActionModal] = useState<SalesOpportunity | null>(null);
  const [probabilityOpportunity, setProbabilityOpportunity] =
    useState<SalesOpportunity | null>(null);
  const [probabilityValue, setProbabilityValue] = useState('');
  const [currencyExpanded, setCurrencyExpanded] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(max-width: 720px)');
    const sync = () => setNarrowViewport(media.matches);
    sync();
    media.addEventListener('change', sync);
    return () => media.removeEventListener('change', sync);
  }, []);

  const replaceUrl = useCallback(
    (
      updates: Record<string, string | number | boolean | null>,
      history: 'push' | 'replace' = 'replace',
    ) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === '' || value === false) next.delete(key);
        else next.set(key, String(value));
      }
      const target = (next.toString() ? `${pathname}?${next.toString()}` : pathname) as Route;
      if (history === 'push') router.push(target);
      else router.replace(target);
    },
    [pathname, router, searchParams],
  );

  const patchFilter = useCallback(
    (patch: Partial<OpportunityWorkspaceFilters>) => {
      const next = { ...filters, ...patch };
      replaceUrl({
        view: next.view === 'board' ? null : next.view,
        q: next.search || null,
        search: null,
        stage: next.stage || null,
        assignee: next.assignee || null,
        priority: next.priority || null,
        archived: next.archived || null,
        sort: next.sort === 'updated_at' ? null : next.sort,
        direction: next.direction === 'desc' ? null : next.direction,
        page: next.page > 1 ? next.page : null,
      });
    },
    [filters, replaceUrl],
  );

  const load = useCallback(async () => {
    if (preview) {
      setLoading(preview.state === 'loading');
      setError(
        preview.state === 'error'
          ? 'Preview error state: opportunities are unavailable.'
          : null,
      );
      const previewItems = preview.state === 'ready' ? preview.items : [];
      setItems(previewItems);
      setServerTotal(previewItems.length);
      return;
    }
    if (!permissions.canView) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetchOpportunities({
        search: filters.search,
        stage: filters.stage || undefined,
        assigned_sales_user_id: filters.assignee || undefined,
        include_archived: filters.archived,
        sort_by: filters.sort,
        sort_dir: filters.direction,
        offset: 0,
        limit: MAX_LIVE_ITEMS,
      });
      setItems(response.items);
      setServerTotal(response.total);
      setSelected((current) => {
        if (!current) return current;
        return response.items.find((item) => item.id === current.id) ?? current;
      });
    } catch (loadError) {
      setItems([]);
      setServerTotal(0);
      setError(
        loadError instanceof ApiError
          ? loadError.message
          : tSales('loadError'),
      );
    } finally {
      setLoading(false);
    }
  }, [
    preview,
    filters.assignee,
    filters.archived,
    filters.direction,
    filters.search,
    filters.sort,
    filters.stage,
    permissions.canView,
    tSales,
  ]);

  useEffect(() => {
    if (preview) {
      void load();
      return;
    }
    if (!permissions.canView) {
      setLoading(false);
      return;
    }
    void load();
  }, [load, permissions.canView, preview]);

  useEffect(() => {
    const handler = () => {
      void load();
    };
    window.addEventListener(CRM_CONTACT_UPDATED_EVENT, handler);
    return () => window.removeEventListener(CRM_CONTACT_UPDATED_EVENT, handler);
  }, [load]);

  useEffect(() => {
    if (preview) {
      setUsers(preview.users);
      setEnrichmentWarning(false);
      return;
    }
    if (!permissions.canView) return;
    setEnrichmentWarning(false);
    void fetchUsers()
      .then((response) => setUsers(response.items))
      .catch(() => {
        setUsers([]);
        setEnrichmentWarning(true);
      });
  }, [permissions.canView, preview]);

  const handleDeepLinkOpen = useCallback((opportunity: SalesOpportunity) => {
    setSelected(opportunity);
  }, []);
  const deepLinkFetcher = useCallback(
    async (id: string) => {
      if (!preview) return fetchOpportunity(id);
      const opportunity = preview.items.find((item) => item.id === id);
      if (!opportunity) throw new Error('Preview opportunity not found');
      return opportunity;
    },
    [preview],
  );
  useRecordDeepLink(deepLinkFetcher, handleDeepLinkOpen, 'opportunity', true);

  useEffect(() => {
    if (!searchParams.get('opportunity')) setSelected(null);
  }, [searchParams]);

  const openOpportunity = useCallback(
    (opportunity: SalesOpportunity) => {
      setSelected(opportunity);
      replaceUrl({ opportunity: opportunity.id }, 'push');
    },
    [replaceUrl],
  );

  const closeOpportunity = useCallback(() => {
    setSelected(null);
    replaceUrl({ opportunity: null }, 'push');
  }, [replaceUrl]);

  const openPipelineCustomer = useCallback(
    (opportunity: SalesOpportunity) => {
      const contactId = opportunityContactId(opportunity);
      if (contactId) {
        setSelected(null);
        openContact(contactId);
        return;
      }
      openOpportunity(opportunity);
    },
    [openContact, openOpportunity],
  );

  const filteredItems = useMemo(
    () => filterOpportunities(items, filters),
    [filters, items],
  );
  const summary = useMemo(() => aggregateOpportunitySummary(filteredItems), [filteredItems]);
  const currencyKpiRows = useMemo(() => {
    const byCode = new Map(summary.currencies.map((entry) => [entry.currency, entry]));
    const defaults = DEFAULT_CURRENCY_KPI.map(
      (currency) => byCode.get(currency) ?? { currency, total: 0, weighted: 0 },
    );
    if (!currencyExpanded) return defaults;
    const extras = summary.currencies.filter(
      (entry) => !DEFAULT_CURRENCY_KPI.includes(entry.currency as (typeof DEFAULT_CURRENCY_KPI)[number]),
    );
    return [...defaults, ...extras];
  }, [currencyExpanded, summary.currencies]);
  const hasExtraCurrencies = summary.currencies.some(
    (entry) => !DEFAULT_CURRENCY_KPI.includes(entry.currency as (typeof DEFAULT_CURRENCY_KPI)[number]),
  );
  const userNames = useMemo(
    () => Object.fromEntries(users.map((entry) => [entry.id, entry.full_name])),
    [users],
  );
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / PAGE_SIZE));
  const safePage = Math.min(filters.page, totalPages);
  const pageItems = useMemo(
    () => filteredItems.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [filteredItems, safePage],
  );

  const updateOpportunityInState = useCallback((updated: SalesOpportunity) => {
    setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    setSelected((current) => (current?.id === updated.id ? updated : current));
  }, []);

  const requestStageChange = useCallback(
    async (
      opportunity: SalesOpportunity,
      targetStage: OpportunityStage,
      payload?: {
        notes?: string;
        loss_reason?: OpportunityLossReason;
        loss_notes?: string;
        dormant_review_date?: string;
        cancelled_reason?: string;
      },
    ) => {
      if (!permissions.canChangeStage) {
        setAnnouncement(t('noStagePermission'));
        return;
      }
      if (!canTransitionStage(opportunity.stage, targetStage)) {
        setAnnouncement(t('invalidTransition'));
        return;
      }
      if (stageRequiresModal(targetStage) && !payload) {
        setStageModal({ opportunity, targetStage });
        return;
      }
      setSubmitting(true);
      const previous = opportunity;
      updateOpportunityInState({ ...opportunity, stage: targetStage });
      try {
        const updated = await changeOpportunityStage(opportunity.id, {
          stage: targetStage,
          ...payload,
        });
        updateOpportunityInState(updated);
        setStageModal(null);
        setAnnouncement(`${updated.opportunity_code}: ${getStageLabel(updated.stage)}`);
      } catch {
        updateOpportunityInState(previous);
        setAnnouncement(t('stageError'));
      } finally {
        setSubmitting(false);
      }
    },
    [
      getStageLabel,
      permissions.canChangeStage,
      t,
      updateOpportunityInState,
    ],
  );

  const dropOnStage = useCallback(
    (stage: OpportunityStage, droppedId?: string) => {
      const id = droppedId || draggingIdRef.current || draggingId;
      const opportunity = items.find((item) => item.id === id);
      draggingIdRef.current = null;
      setDraggingId(null);
      setOverStage(null);
      if (!opportunity || opportunity.stage === stage) return;
      void requestStageChange(opportunity, stage);
    },
    [draggingId, items, requestStageChange],
  );

  const saveNextAction = async (
    nextAction: OpportunityNextAction,
    nextActionDate: string,
  ) => {
    if (!nextActionModal || !permissions.canUpdate) return;
    setSubmitting(true);
    try {
      const updated = await updateOpportunityNextAction(nextActionModal.id, {
        next_action: nextAction,
        next_action_date: nextActionDate,
      });
      updateOpportunityInState(updated);
      setNextActionModal(null);
      setAnnouncement(t('nextActionUpdated'));
    } catch {
      setAnnouncement(tSales('errors.nextActionFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const saveProbability = async () => {
    if (!probabilityOpportunity || !permissions.canChangeProbability) return;
    const probability = Number(probabilityValue);
    if (!Number.isInteger(probability) || probability < 0 || probability > 100) {
      setAnnouncement(t('probabilityInvalid'));
      return;
    }
    setSubmitting(true);
    try {
      const updated = await changeOpportunityProbability(probabilityOpportunity.id, {
        probability,
      });
      updateOpportunityInState(updated);
      setProbabilityOpportunity(null);
      setProbabilityValue('');
      setAnnouncement(t('probabilityUpdated'));
    } catch {
      setAnnouncement(t('probabilityFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const submitCreate = async (input: SalesOpportunityInput) => {
    if (!permissions.canCreate) return;
    setSubmitting(true);
    try {
      const created = await createOpportunity(input);
      setCreateOpen(false);
      await load();
      openOpportunity(created);
    } catch {
      setAnnouncement(tSales('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const toggleArchive = async (opportunity: SalesOpportunity) => {
    const allowed = opportunity.archived_at ? permissions.canRestore : permissions.canArchive;
    if (!allowed) return;
    setSubmitting(true);
    try {
      const updated = opportunity.archived_at
        ? await restoreOpportunity(opportunity.id)
        : await archiveOpportunity(opportunity.id);
      updateOpportunityInState(updated);
      closeOpportunity();
      await load();
    } catch {
      setAnnouncement(
        opportunity.archived_at ? tSales('restoreError') : tSales('archiveError'),
      );
    } finally {
      setSubmitting(false);
    }
  };

  const clearFilters = () => {
    replaceUrl({
      view: filters.view === 'board' ? null : filters.view,
      q: null,
      search: null,
      stage: null,
      assignee: null,
      priority: null,
      archived: null,
      sort: null,
      direction: null,
      page: null,
    });
  };

  const activeChips = [
    filters.search ? { key: 'search', label: `${t('searchChip')}: ${filters.search}` } : null,
    filters.stage ? { key: 'stage', label: getStageLabel(filters.stage) } : null,
    filters.assignee
      ? { key: 'assignee', label: userNames[filters.assignee] ?? filters.assignee }
      : null,
    filters.priority
      ? { key: 'priority', label: getPriorityLabel(filters.priority) }
      : null,
    filters.archived ? { key: 'archived', label: tSales('filters.includeArchived') } : null,
  ].filter((chip): chip is { key: string; label: string } => Boolean(chip));

  if (authLoading) return <LoadingState label={tCommon('loading')} variant="skeleton" lines={6} />;
  if (!preview && !user) return <LoadingState label={tCommon('loading')} />;
  if (!permissions.canView) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  return (
    <div className="opportunities-workspace" data-testid="crm-opportunities-workspace">
      <PageHeader
        title={t('title')}
        subtitle={`${t('subtitle')} · ${t('liveCount', { count: filteredItems.length })}`}
        actions={
          <div className="opportunities-workspace__header-actions">
            <SegmentedControl
              ariaLabel={t('viewLabel')}
              value={effectiveView}
              options={[
                { value: 'board', label: t('board'), disabled: !permissions.canViewBoard },
                { value: 'list', label: t('list') },
              ]}
              onChange={(view) => patchFilter({ view, page: 1 })}
            />
            {permissions.canCreate ? (
              <Button className="opportunities-workspace__create" onClick={() => setCreateOpen(true)}>
                <IhIcon name="plus" size={14} />
                {tSales('createButton')}
              </Button>
            ) : null}
          </div>
        }
      />

      <section className="opportunities-summary" aria-label={t('summaryAria')}>
        <article
          className="ih-kpi-card opportunities-summary__kpi opportunities-summary__kpi--open"
          aria-label={t('openCount')}
        >
          <span className="ih-kpi-card__icon" aria-hidden="true">
            <IhIcon name="sales" size={28} />
          </span>
          <div className="opportunities-summary__kpi-body">
            <strong className="ih-kpi-card__value">{summary.openCount}</strong>
            <div className="ih-kpi-card__hint">
              <span>{t('kpiHintTotal')}</span>
              <span>{t('kpiHintLive')}</span>
            </div>
          </div>
        </article>
        <article
          className="ih-kpi-card opportunities-summary__kpi opportunities-summary__kpi--missing"
          aria-label={t('missingNextAction')}
        >
          <span className="ih-kpi-card__icon" aria-hidden="true">
            <IhIcon name="clock" size={28} />
          </span>
          <div className="opportunities-summary__kpi-body">
            <strong className="ih-kpi-card__value">{summary.missingNextAction}</strong>
            <div className="ih-kpi-card__hint">
              <span>{t('kpiHintAction')}</span>
              <span>{t('kpiHintNeedsAssign')}</span>
            </div>
          </div>
        </article>
        <article
          className="ih-kpi-card opportunities-summary__kpi opportunities-summary__kpi--overdue"
          aria-label={t('overdueNextAction')}
        >
          <span className="ih-kpi-card__icon" aria-hidden="true">
            <IhIcon name="alert" size={28} />
          </span>
          <div className="opportunities-summary__kpi-body">
            <strong className="ih-kpi-card__value">{summary.overdueNextAction}</strong>
            <div className="ih-kpi-card__hint">
              <span>{t('kpiHintAction')}</span>
              <span>{t('kpiHintPastDue')}</span>
            </div>
          </div>
        </article>
        <article
          className={`ih-kpi-card ih-kpi-card--primary opportunities-summary__currency${
            currencyExpanded ? ' is-expanded' : ''
          }`}
          aria-label={t('pipelineByCurrency')}
        >
          {permissions.canViewSensitiveValues ? (
            <div className="opportunities-currency-summary">
              <div
                className="opportunities-currency-summary__list"
                data-expanded={currencyExpanded ? 'true' : 'false'}
              >
                {currencyKpiRows.map((entry) => (
                  <div
                    key={entry.currency}
                    className="opportunities-currency-summary__row"
                    data-currency={entry.currency}
                  >
                    <span className="opportunities-currency-summary__glyph" aria-hidden="true">
                      {currencyGlyph(entry.currency)}
                    </span>
                    <strong>{entry.currency}</strong>
                    <span>
                      <span>
                        {t('totalShort')}{' '}
                        {formatMoney(String(entry.total), entry.currency, locale)}
                      </span>
                      <small>
                        {t('weighted')}{' '}
                        {formatMoney(String(entry.weighted), entry.currency, locale)}
                      </small>
                    </span>
                  </div>
                ))}
              </div>
              {hasExtraCurrencies ? (
                <button
                  type="button"
                  className="opportunities-currency-summary__toggle"
                  aria-expanded={currencyExpanded}
                  onClick={() => setCurrencyExpanded((current) => !current)}
                >
                  <span>{currencyExpanded ? t('showFewerCurrencies') : t('seeAllCurrencies')}</span>
                  <IhIcon name="chevronDown" size={14} />
                </button>
              ) : null}
            </div>
          ) : (
            <>
              <strong className="ih-kpi-card__value">••••</strong>
              <span className="ih-kpi-card__hint">{t('sensitiveHidden')}</span>
            </>
          )}
        </article>
      </section>

      <section className="opportunities-controls" aria-label={t('filtersAria')}>
        <FilterBar
          actions={
            <div className="opportunities-controls__actions">
              <StatusChip tone="info">{t('resultCount', { count: filteredItems.length })}</StatusChip>
              <Button variant="ghost" onClick={clearFilters} disabled={!activeChips.length}>
                {t('clearFilters')}
              </Button>
            </div>
          }
        >
          <SearchInput
            label={tSales('filters.search')}
            value={filters.search}
            placeholder={tSales('filters.searchPlaceholder')}
            onChange={(event) => patchFilter({ search: event.target.value, page: 1 })}
            onClear={() => patchFilter({ search: '', page: 1 })}
          />
          <Select
            label={tSales('filters.stage')}
            value={filters.stage}
            onChange={(event) =>
              patchFilter({ stage: event.target.value as OpportunityStage | '', page: 1 })
            }
          >
            <option value="">{tSales('filters.allStages')}</option>
            {OPPORTUNITY_STAGE_ORDER.map((stage) => (
              <option key={stage} value={stage}>{getStageLabel(stage)}</option>
            ))}
          </Select>
          <Select
            label={tSales('filters.assignee')}
            value={filters.assignee}
            onChange={(event) => patchFilter({ assignee: event.target.value, page: 1 })}
          >
            <option value="">{tSales('filters.allAssignees')}</option>
            {users.map((entry) => (
              <option key={entry.id} value={entry.id}>{entry.full_name}</option>
            ))}
          </Select>
          <Select
            label={tSales('filters.priority')}
            value={filters.priority}
            onChange={(event) =>
              patchFilter({
                priority: event.target.value as OpportunityPriority | '',
                page: 1,
              })
            }
          >
            <option value="">{tSales('filters.allPriorities')}</option>
            {(['low', 'medium', 'high', 'urgent'] as const).map((priority) => (
              <option key={priority} value={priority}>{getPriorityLabel(priority)}</option>
            ))}
          </Select>
          <Select
            label={t('sortLabel')}
            value={filters.sort}
            onChange={(event) => patchFilter({ sort: event.target.value, page: 1 })}
          >
            <option value="updated_at">{tSales('table.updated')}</option>
            <option value="expected_close_date">{tSales('table.expectedClose')}</option>
            <option value="opportunity_code">{tSales('table.code')}</option>
            <option value="stage">{tSales('table.stage')}</option>
          </Select>
          <Select
            label={t('directionLabel')}
            value={filters.direction}
            onChange={(event) =>
              patchFilter({ direction: event.target.value as 'asc' | 'desc', page: 1 })
            }
          >
            <option value="desc">{t('descending')}</option>
            <option value="asc">{t('ascending')}</option>
          </Select>
          <label className="opportunities-controls__check">
            <input
              type="checkbox"
              checked={filters.archived}
              onChange={(event) => patchFilter({ archived: event.target.checked, page: 1 })}
            />
            <span>{tSales('filters.includeArchived')}</span>
          </label>
        </FilterBar>
        {activeChips.length ? (
          <div className="opportunities-filter-chips" aria-label={t('activeFiltersAria')}>
            {activeChips.map((chip) => (
              <button
                key={chip.key}
                type="button"
                onClick={() => {
                  if (chip.key === 'search') patchFilter({ search: '', page: 1 });
                  if (chip.key === 'stage') patchFilter({ stage: '', page: 1 });
                  if (chip.key === 'assignee') patchFilter({ assignee: '', page: 1 });
                  if (chip.key === 'priority') patchFilter({ priority: '', page: 1 });
                  if (chip.key === 'archived') patchFilter({ archived: false, page: 1 });
                }}
              >
                {chip.label} ×
              </button>
            ))}
          </div>
        ) : null}
      </section>

      {serverTotal > items.length || enrichmentWarning ? (
        <div className="opportunities-result-status" role="status" aria-live="polite">
          {serverTotal > items.length ? (
            <span>{t('partialResult', { visible: items.length, total: serverTotal })}</span>
          ) : null}
          {enrichmentWarning ? <span>{t('teamNamesUnavailable')}</span> : null}
        </div>
      ) : null}
      {announcement ? (
        <div className="crm-g2-toast" role="status">
          {announcement}
          <button type="button" onClick={() => setAnnouncement(null)} aria-label={tCommon('close')}>×</button>
        </div>
      ) : null}

      {error ? (
        <ErrorState
          title={tSales('loadErrorTitle')}
          message={error}
          action={<Button onClick={() => void load()}>{tCommon('retry')}</Button>}
        />
      ) : loading && !items.length ? (
        <LoadingState label={t('loading')} variant="skeleton" lines={8} />
      ) : !filteredItems.length ? (
        <EmptyState
          title={items.length ? t('noMatches') : tSales('empty')}
          description={items.length ? t('adjustFilters') : tSales('emptyHint')}
          action={items.length ? <Button onClick={clearFilters}>{t('clearFilters')}</Button> : undefined}
        />
      ) : effectiveView === 'board' ? (
        <div className="opportunities-board-shell" data-testid="opportunities-board-shell">
          <div className="opportunities-board" role="list" aria-label={t('boardStagesAria')}>
            {OPPORTUNITY_STAGE_ORDER.map((stage) => {
              const stageItems = filteredItems.filter((item) => item.stage === stage);
              const totals = stageCurrencyTotals(stageItems, stage);
              return (
                <section
                  key={stage}
                  className={`opportunities-column${overStage === stage ? ' is-over' : ''}`}
                  role="listitem"
                  data-stage={stage}
                  onDragOver={(event) => {
                    if (!permissions.canChangeStage) return;
                    event.preventDefault();
                    event.dataTransfer.dropEffect = 'move';
                    setOverStage(stage);
                  }}
                  onDragLeave={(event) => {
                    const next = event.relatedTarget as Node | null;
                    if (next && event.currentTarget.contains(next)) return;
                    setOverStage((current) => (current === stage ? null : current));
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    const droppedId =
                      event.dataTransfer.getData('application/x-opportunity-id') ||
                      event.dataTransfer.getData('text/plain');
                    dropOnStage(stage, droppedId || undefined);
                  }}
                >
                  <header className="opportunities-column__header">
                    <div>
                      <strong>{getStageLabel(stage)}</strong>
                    </div>
                    <span className="opportunities-column__count">{stageItems.length}</span>
                    <small>
                      {permissions.canViewSensitiveValues
                        ? totals.length
                          ? totals
                              .map(
                                (entry) =>
                                  `${formatMoney(String(entry.total), entry.currency, locale)} · ${t('weightedShort')} ${formatMoney(String(entry.weighted), entry.currency, locale)}`,
                              )
                              .join(' · ')
                          : '—'
                        : '••••'}
                    </small>
                  </header>
                  <div className="opportunities-column__cards">
                    {stageItems.length ? stageItems.map((opportunity) => {
                      const cardContext = getOpportunityCardContext(
                        opportunity,
                        preview?.cardContext,
                      );
                      return (
                        <OpportunityCard
                          key={opportunity.id}
                          opportunity={opportunity}
                          assigneeName={
                            opportunity.assigned_sales_user_id
                              ? userNames[opportunity.assigned_sales_user_id]
                              : undefined
                          }
                          customerName={cardContext.customerName ?? opportunity.party_label}
                          projectName={cardContext.projectName}
                          canViewSensitiveValues={permissions.canViewSensitiveValues}
                          draggable={permissions.canChangeStage}
                          dragging={draggingId === opportunity.id}
                          selected={selected?.id === opportunity.id}
                          onOpen={() => openPipelineCustomer(opportunity)}
                          onDragStart={() => {
                            draggingIdRef.current = opportunity.id;
                            setDraggingId(opportunity.id);
                          }}
                          onDragEnd={() => {
                            draggingIdRef.current = null;
                            setDraggingId(null);
                            setOverStage(null);
                          }}
                        />
                      );
                    }) : <p className="opportunities-column__empty">{t('emptyStage')}</p>}
                    {permissions.canCreate ? (
                      <button
                        type="button"
                        className="opportunities-column__add"
                        onClick={() => setCreateOpen(true)}
                      >
                        <IhIcon name="plus" size={12} />
                        {t('addOpportunity')}
                      </button>
                    ) : null}
                  </div>
                </section>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="opportunities-list">
          <TableToolbar
            className="opportunities-list__toolbar"
            actions={<StatusChip tone="info">{t('resultCount', { count: filteredItems.length })}</StatusChip>}
          >
            <strong>{t('list')}</strong>
          </TableToolbar>
          <Table className="ih-table opportunities-table" wrapClassName="ih-table-wrap opportunities-list__table">
              <thead>
                <tr>
                  <th>{t('listCols.opportunity')}</th>
                  <th>{t('listCols.stage')}</th>
                  <th>{t('listCols.revenue')}</th>
                      <th>{t('weighted')}</th>
                  <th>{t('listCols.probability')}</th>
                  <th>{tSales('table.assignee')}</th>
                  <th>{tSales('table.priority')}</th>
                  <th>{tSales('table.nextAction')}</th>
                  <th>{t('listCols.closeDate')}</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((opportunity) => {
                  const expected = opportunity.expected_revenue
                    ? Number(opportunity.expected_revenue)
                    : null;
                  return (
                    <tr
                      key={opportunity.id}
                      onClick={() => openPipelineCustomer(opportunity)}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault();
                          openPipelineCustomer(opportunity);
                        }
                      }}
                      tabIndex={0}
                    >
                      <td><strong>{opportunity.display_id ?? opportunity.opportunity_code}</strong></td>
                      <td>{getStageLabel(opportunity.stage)}</td>
                      <td>
                        {permissions.canViewSensitiveValues
                          ? formatMoney(opportunity.expected_revenue, opportunity.currency, locale)
                          : '••••'}
                      </td>
                      <td>
                        {permissions.canViewSensitiveValues && expected !== null
                          ? formatMoney(
                              String(expected * opportunity.probability / 100),
                              opportunity.currency,
                              locale,
                            )
                          : '••••'}
                      </td>
                      <td>{opportunity.probability}%</td>
                      <td>
                        {opportunity.assigned_sales_user_id
                          ? userNames[opportunity.assigned_sales_user_id] ?? '—'
                          : '—'}
                      </td>
                      <td><StatusChip tone={priorityTone(opportunity.priority)}>{getPriorityLabel(opportunity.priority)}</StatusChip></td>
                      <td className={isOpportunityOverdue(opportunity) ? 'is-overdue' : undefined}>
                        {opportunity.next_action
                          ? getNextActionLabel(opportunity.next_action)
                          : '—'}
                        {opportunity.next_action_date
                          ? ` · ${formatShortDate(opportunity.next_action_date, locale)}`
                          : ''}
                      </td>
                      <td>{formatShortDate(opportunity.expected_close_date, locale)}</td>
                    </tr>
                  );
                })}
              </tbody>
          </Table>
          {filteredItems.length > PAGE_SIZE ? (
            <Pagination
              page={safePage}
              pageSize={PAGE_SIZE}
              total={filteredItems.length}
              previousLabel={tSales('prevPage')}
              nextLabel={tSales('nextPage')}
              summary={`${safePage} / ${totalPages}`}
              onPrevious={() => patchFilter({ page: Math.max(1, safePage - 1) })}
              onNext={() => patchFilter({ page: Math.min(totalPages, safePage + 1) })}
            />
          ) : null}
        </div>
      )}

      <CrmRecordDrawer
        key={selected?.id ?? 'closed-opportunity'}
        open={Boolean(selected)}
        onClose={closeOpportunity}
        title={selected ? selected.display_id ?? selected.opportunity_code : ''}
        subtitle={selected ? getStageLabel(selected.stage) : undefined}
        badge={
          selected
            ? <StatusChip tone={priorityTone(selected.priority)}>{getPriorityLabel(selected.priority)}</StatusChip>
            : null
        }
        summary={
          selected ? (
            <dl className="crm-g2-drawer__grid">
              <CrmDrawerField label={t('listCols.stage')} value={getStageLabel(selected.stage)} />
              <CrmDrawerField label={t('listCols.probability')} value={`${selected.probability}%`} />
              <CrmDrawerField
                label={t('listCols.revenue')}
                value={
                  permissions.canViewSensitiveValues
                    ? formatMoney(selected.expected_revenue, selected.currency, locale)
                    : '••••'
                }
              />
              <CrmDrawerField
                label={tSales('table.assignee')}
                value={
                  selected.assigned_sales_user_id
                    ? userNames[selected.assigned_sales_user_id] ?? '—'
                    : '—'
                }
              />
              <CrmDrawerField
                label={t('listCols.closeDate')}
                value={formatShortDate(selected.expected_close_date, locale)}
              />
              <CrmDrawerField label={tSales('form.source')} value={selected.source ?? '—'} />
            </dl>
          ) : null
        }
        sections={
          selected ? {
            timeline: (
              <OpportunityDetailSections
                opportunity={selected}
                mode="timeline"
                preview={preview?.details}
                {...permissions}
              />
            ),
            nextAction: (
              <OpportunityDetailSections
                opportunity={selected}
                mode="nextAction"
                preview={preview?.details}
                {...permissions}
              />
            ),
            customer: (
              <OpportunityDetailSections
                opportunity={selected}
                mode="customer"
                preview={preview?.details}
                {...permissions}
              />
            ),
            ...(permissions.canViewProposals ? {
              proposal: (
                <OpportunityDetailSections
                  opportunity={selected}
                  mode="proposal"
                  preview={preview?.details}
                  {...permissions}
                />
              ),
            } : {}),
            ...(permissions.canViewReservations ? {
              reservation: (
                <OpportunityDetailSections
                  opportunity={selected}
                  mode="reservation"
                  preview={preview?.details}
                  {...permissions}
                />
              ),
            } : {}),
            ai: (
              <OpportunityDetailSections
                opportunity={selected}
                mode="ai"
                preview={preview?.details}
                {...permissions}
              />
            ),
          } : {}
        }
        footer={
          selected ? (
            <div className="opportunity-drawer-actions">
              {permissions.canChangeStage ? (
                <Button variant="secondary" onClick={() => setStageModal({ opportunity: selected, targetStage: null })}>
                  {tSales('detail.changeStage')}
                </Button>
              ) : null}
              {permissions.canChangeProbability ? (
                <Button
                  variant="secondary"
                  onClick={() => {
                    setProbabilityOpportunity(selected);
                    setProbabilityValue(String(selected.probability));
                  }}
                >
                  {t('changeProbability')}
                </Button>
              ) : null}
              {permissions.canUpdate ? (
                <Button variant="secondary" onClick={() => setNextActionModal(selected)}>
                  {tSales('detail.editNextAction')}
                </Button>
              ) : null}
              {selected.archived_at ? (
                permissions.canRestore ? (
                  <Button variant="secondary" disabled={submitting} onClick={() => void toggleArchive(selected)}>
                    {tSales('detail.restore')}
                  </Button>
                ) : null
              ) : permissions.canArchive ? (
                <Button variant="danger" disabled={submitting} onClick={() => void toggleArchive(selected)}>
                  {tSales('detail.archive')}
                </Button>
              ) : null}
            </div>
          ) : null
        }
      />

      {createOpen ? (
        <SalesFormModal
          mode="create"
          users={users}
          submitting={submitting}
          onClose={() => setCreateOpen(false)}
          onSubmit={(input) => void submitCreate(input)}
        />
      ) : null}
      {stageModal ? (
        <SalesStageChangeModal
          opportunity={stageModal.opportunity}
          targetStage={stageModal.targetStage}
          submitting={submitting}
          onClose={() => setStageModal(null)}
          onSubmit={(payload) =>
            void requestStageChange(stageModal.opportunity, payload.stage, payload)
          }
        />
      ) : null}
      {nextActionModal ? (
        <SalesNextActionModal
          opportunity={nextActionModal}
          submitting={submitting}
          onClose={() => setNextActionModal(null)}
          onSubmit={(action, date) => void saveNextAction(action, date)}
        />
      ) : null}
      {probabilityOpportunity ? (
        <div className="leads-modal" role="presentation" onClick={() => setProbabilityOpportunity(null)}>
          <form
            className="leads-modal__panel opportunity-probability-dialog"
            role="dialog"
            aria-modal="true"
            aria-label={t('changeProbability')}
            onClick={(event) => event.stopPropagation()}
            onSubmit={(event) => {
              event.preventDefault();
              void saveProbability();
            }}
          >
            <h2>{t('changeProbability')}</h2>
            <label className="leads__field">
              <span>{t('probability')}</span>
              <input
                type="number"
                min={0}
                max={100}
                step={1}
                value={probabilityValue}
                onChange={(event) => setProbabilityValue(event.target.value)}
                autoFocus
                required
              />
            </label>
            <div className="opportunity-drawer-actions">
              <Button type="button" variant="ghost" onClick={() => setProbabilityOpportunity(null)}>
                {tCommon('cancel')}
              </Button>
              <Button type="submit" disabled={submitting}>{t('save')}</Button>
            </div>
          </form>
        </div>
      ) : null}
    </div>
  );
}
