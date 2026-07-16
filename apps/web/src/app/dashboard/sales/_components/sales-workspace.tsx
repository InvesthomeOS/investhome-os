'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { hasPermission, fetchUsers, type UserRecord } from '@/lib/api/auth';
import { fetchLead } from '@/lib/api/leads';
import { fetchInvestor } from '@/lib/api/investors';
import { fetchInventoryAssets } from '@/lib/api/inventory';
import { fetchProjects, type Project } from '@/lib/api/projects';
import {
  archiveOpportunity,
  changeOpportunityStage,
  createOpportunity,
  fetchOpportunities,
  fetchOpportunity,
  fetchSalesHomeKpis,
  linkOpportunityInventory,
  linkOpportunityProject,
  restoreOpportunity,
  stageRequiresModal,
  updateOpportunity,
  updateOpportunityNextAction,
  type SalesHomeKpis,
  type SalesKpiKey,
  type SalesOpportunity,
  type SalesOpportunityInput,
  type OpportunityStage,
  type OpportunityLossReason,
} from '@/lib/api/sales';
import { useAuth } from '@/lib/auth/auth-context';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

import { SalesDetailDrawer } from './sales-detail-drawer';
import { SalesFilters, type SalesFilterState } from './sales-filters';
import { SalesFormModal } from './sales-form-modal';
import { SalesKpiRow } from './sales-kpi-row';
import { SalesNextActionModal } from './sales-next-action-modal';
import { SalesOpportunityTable } from './sales-opportunity-table';
import { SalesPipelineKanban } from './sales-pipeline-kanban';
import { SalesStageChangeModal } from './sales-stage-change-modal';

const FILTER_STORAGE_KEY = 'investhome.sales.filters';
const PAGE_SIZE = 20;

type FormMode = 'create' | 'edit' | null;

const EMPTY_FILTERS: SalesFilterState = {
  search: '',
  stage: '',
  assigned_sales_user_id: '',
  party_id: '',
  lead_id: '',
  priority: '',
  include_archived: false,
  sort_by: 'updated_at',
  sort_dir: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
  view: 'pipeline',
};

function loadStoredFilters(): SalesFilterState {
  if (typeof window === 'undefined') return EMPTY_FILTERS;
  try {
    const raw = localStorage.getItem(FILTER_STORAGE_KEY);
    if (!raw) return EMPTY_FILTERS;
    return { ...EMPTY_FILTERS, ...JSON.parse(raw) };
  } catch {
    return EMPTY_FILTERS;
  }
}

function kpiToFilter(key: SalesKpiKey): Partial<SalesFilterState> {
  switch (key) {
    case 'new_leads':
      return { view: 'list', stage: '', search: '' };
    case 'qualified_leads':
      return { view: 'list', stage: 'qualified' };
    case 'active_opportunities':
      return { view: 'list', stage: '' };
    case 'meetings_scheduled':
      return { view: 'list', stage: 'meeting_scheduled' };
    case 'proposals_pending':
      return { view: 'list', stage: 'proposal_sent' };
    case 'active_soft_holds':
      return { view: 'list', stage: 'soft_hold' };
    case 'reservations_pending':
      return { view: 'list', stage: 'reservation' };
    case 'deposits_pending':
      return { view: 'list', stage: 'deposit_pending' };
    case 'under_contract':
      return { view: 'list', stage: 'contract' };
    case 'won_this_month':
      return { view: 'list', stage: 'won' };
    case 'lost_this_month':
      return { view: 'list', stage: 'lost' };
    default:
      return { view: 'list' };
  }
}

export function SalesWorkspace() {
  const t = useTranslations('sales');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getErrorMessage } = useSalesLabels();

  const [filters, setFilters] = useState<SalesFilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<SalesFilterState>(EMPTY_FILTERS);
  const [kpis, setKpis] = useState<SalesHomeKpis | null>(null);
  const [kpisLoading, setKpisLoading] = useState(true);
  const [activeKpi, setActiveKpi] = useState<SalesKpiKey | null>(null);
  const [opportunities, setOpportunities] = useState<SalesOpportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [partyNames, setPartyNames] = useState<Record<string, string>>({});
  const [userNames, setUserNames] = useState<Record<string, string>>({});
  const [linkedProjects, setLinkedProjects] = useState<Record<string, string[]>>({});
  const [linkedInventory, setLinkedInventory] = useState<Record<string, string[]>>({});
  const [inventoryLabels, setInventoryLabels] = useState<Record<string, string>>({});
  const [selectedOpportunity, setSelectedOpportunity] = useState<SalesOpportunity | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [createLeadId, setCreateLeadId] = useState<string | null>(null);
  const [stageModal, setStageModal] = useState<{ opportunity: SalesOpportunity; stage: OpportunityStage | null } | null>(null);
  const [nextActionModal, setNextActionModal] = useState<SalesOpportunity | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [density, setDensity] = useState<'comfortable' | 'compact'>('comfortable');
  const [toastError, setToastError] = useState<string | null>(null);

  const canView = user ? hasPermission(user, 'sales', 'view') || hasPermission(user, 'leads', 'view') : false;
  const canCreate = user ? hasPermission(user, 'sales', 'create') : false;
  const canUpdate = user ? hasPermission(user, 'sales', 'update') : false;
  const canChangeStage = user ? hasPermission(user, 'sales', 'change_stage') : false;
  const canArchive = user ? hasPermission(user, 'sales', 'archive') : false;
  const canRestore = user ? hasPermission(user, 'sales', 'restore') : false;
  const canViewPipeline = user ? hasPermission(user, 'sales', 'view_pipeline') : false;
  const canViewSensitiveValue = user ? hasPermission(user, 'sales', 'view_sensitive_value') : false;

  useEffect(() => {
    setFilters(loadStoredFilters());
    setAppliedFilters(loadStoredFilters());
  }, []);

  const kpiLabels = useMemo(
    (): Record<SalesKpiKey, string> => ({
      new_leads: t('kpis.newLeads'),
      qualified_leads: t('kpis.qualifiedLeads'),
      active_opportunities: t('kpis.activeOpportunities'),
      pipeline_value: t('kpis.pipelineValue'),
      weighted_pipeline: t('kpis.weightedPipeline'),
      meetings_scheduled: t('kpis.meetingsScheduled'),
      proposals_pending: t('kpis.proposalsPending'),
      active_soft_holds: t('kpis.activeSoftHolds'),
      reservations_pending: t('kpis.reservationsPending'),
      deposits_pending: t('kpis.depositsPending'),
      under_contract: t('kpis.underContract'),
      won_this_month: t('kpis.wonThisMonth'),
      lost_this_month: t('kpis.lostThisMonth'),
    }),
    [t],
  );

  const loadKpis = useCallback(async () => {
    setKpisLoading(true);
    try {
      setKpis(await fetchSalesHomeKpis());
    } catch {
      setKpis(null);
    } finally {
      setKpisLoading(false);
    }
  }, []);

  const resolvePartyNames = useCallback(async (items: SalesOpportunity[]) => {
    const next: Record<string, string> = {};
    await Promise.all(
      items.map(async (item) => {
        if (partyNames[item.party_id]) {
          next[item.party_id] = partyNames[item.party_id]!;
          return;
        }
        try {
          if (item.party_type === 'lead') {
            const lead = await fetchLead(item.party_id);
            next[item.party_id] = lead.full_name;
          } else {
            const investor = await fetchInvestor(item.party_id);
            next[item.party_id] = investor.full_name;
          }
        } catch {
          next[item.party_id] = item.party_id;
        }
      }),
    );
    setPartyNames((current) => ({ ...current, ...next }));
  }, [partyNames]);

  const loadOpportunities = useCallback(
    async (nextFilters: SalesFilterState) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchOpportunities({
          search: nextFilters.search,
          stage: nextFilters.stage || undefined,
          assigned_sales_user_id: nextFilters.assigned_sales_user_id || undefined,
          party_id: nextFilters.party_id || undefined,
          lead_id: nextFilters.lead_id || undefined,
          include_archived: nextFilters.include_archived,
          sort_by: nextFilters.sort_by,
          sort_dir: nextFilters.sort_dir,
          offset: (nextFilters.page - 1) * nextFilters.page_size,
          limit: nextFilters.view === 'pipeline' ? 200 : nextFilters.page_size,
        });
        let items = response.items;
        if (nextFilters.priority) {
          items = items.filter((item) => item.priority === nextFilters.priority);
        }
        setOpportunities(items);
        setTotal(response.total);
        void resolvePartyNames(items);
      } catch {
        setError(t('loadError'));
        setOpportunities([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [resolvePartyNames, t],
  );

  useEffect(() => {
    if (!canView) return;
    void loadKpis();
    void fetchUsers().then((response) => {
      setUsers(response.items);
      setUserNames(Object.fromEntries(response.items.map((u) => [u.id, u.full_name])));
    });
    void fetchProjects().then((response) => setProjects(response.items));
  }, [canView, loadKpis]);

  useEffect(() => {
    if (!canView) return;
    void loadOpportunities(appliedFilters);
    localStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(appliedFilters));
  }, [appliedFilters, canView, loadOpportunities]);

  const handleOpenOpportunity = useCallback((opportunity: SalesOpportunity) => {
    setSelectedOpportunity(opportunity);
    setActionError(null);
  }, []);

  useRecordDeepLink(fetchOpportunity, handleOpenOpportunity);

  const handleApplyFilters = () => setAppliedFilters({ ...filters, page: 1 });
  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setActiveKpi(null);
  };

  const handleKpiClick = (key: SalesKpiKey) => {
    setActiveKpi(key);
    if (key === 'new_leads' || key === 'qualified_leads') {
      window.location.href = '/dashboard/leads';
      return;
    }
    const next = { ...appliedFilters, ...kpiToFilter(key), page: 1 };
    setFilters(next);
    setAppliedFilters(next);
  };

  const refreshAll = async () => {
    await Promise.all([loadKpis(), loadOpportunities(appliedFilters)]);
  };

  const handleStageChangeRequest = async (
    opportunity: SalesOpportunity,
    stage: OpportunityStage,
    payload?: {
      notes?: string;
      loss_reason?: OpportunityLossReason;
      loss_notes?: string;
      dormant_review_date?: string;
      cancelled_reason?: string;
    },
  ) => {
    if (stageRequiresModal(stage) && !payload) {
      setStageModal({ opportunity, stage });
      return;
    }
    setSubmitting(true);
    setActionError(null);
    try {
      const updated = await changeOpportunityStage(opportunity.id, {
        stage,
        ...payload,
      });
      setOpportunities((current) => current.map((o) => (o.id === updated.id ? updated : o)));
      setSelectedOpportunity((current) => (current?.id === updated.id ? updated : current));
      setStageModal(null);
      await loadKpis();
    } catch (err) {
      const message =
        err instanceof ApiError
          ? getErrorMessage(err.message, t('errors.stageChangeFailed'))
          : t('errors.stageChangeFailed');
      setToastError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleKanbanStageChange = (opportunity: SalesOpportunity, stage: OpportunityStage) => {
    if (stageRequiresModal(stage)) {
      setStageModal({ opportunity, stage });
      return;
    }
    void handleStageChangeRequest(opportunity, stage);
  };

  const handleSubmitOpportunity = async (input: SalesOpportunityInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (formMode === 'create') {
        const created = await createOpportunity(input);
        setOpportunities((current) => [created, ...current]);
        setSelectedOpportunity(created);
      } else if (formMode === 'edit' && selectedOpportunity) {
        const updated = await updateOpportunity(selectedOpportunity.id, input);
        setOpportunities((current) => current.map((o) => (o.id === updated.id ? updated : o)));
        setSelectedOpportunity(updated);
      }
      setFormMode(null);
      setCreateLeadId(null);
      await loadKpis();
    } catch {
      setActionError(t('saveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchive = async (opportunity: SalesOpportunity) => {
    setSubmitting(true);
    try {
      await archiveOpportunity(opportunity.id);
      setOpportunities((current) => current.filter((o) => o.id !== opportunity.id));
      setSelectedOpportunity(null);
      await loadKpis();
    } catch {
      setActionError(t('archiveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRestore = async (opportunity: SalesOpportunity) => {
    setSubmitting(true);
    try {
      const restored = await restoreOpportunity(opportunity.id);
      setOpportunities((current) => [restored, ...current]);
      setSelectedOpportunity(restored);
      await loadKpis();
    } catch {
      setActionError(t('restoreError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextActionSave = async (nextAction: string, nextActionDate: string) => {
    if (!nextActionModal) return;
    setSubmitting(true);
    try {
      const updated = await updateOpportunityNextAction(nextActionModal.id, {
        next_action: nextAction as SalesOpportunity['next_action'] & string,
        next_action_date: nextActionDate,
      });
      setOpportunities((current) => current.map((o) => (o.id === updated.id ? updated : o)));
      setSelectedOpportunity((current) => (current?.id === updated.id ? updated : current));
      setNextActionModal(null);
    } catch {
      setActionError(t('errors.nextActionFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLinkProject = async (opportunity: SalesOpportunity) => {
    const projectId = window.prompt(t('detail.linkProjectPrompt'));
    if (!projectId?.trim()) return;
    setSubmitting(true);
    try {
      await linkOpportunityProject(opportunity.id, { project_id: projectId.trim() });
      setLinkedProjects((current) => ({
        ...current,
        [opportunity.id]: [...(current[opportunity.id] ?? []), projectId.trim()],
      }));
    } catch {
      setActionError(t('errors.linkProjectFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLinkInventory = async (opportunity: SalesOpportunity) => {
    const assetId = window.prompt(t('detail.linkInventoryPrompt'));
    if (!assetId?.trim()) return;
    setSubmitting(true);
    try {
      await linkOpportunityInventory(opportunity.id, { inventory_asset_id: assetId.trim() });
      setLinkedInventory((current) => ({
        ...current,
        [opportunity.id]: [...(current[opportunity.id] ?? []), assetId.trim()],
      }));
      const asset = await fetchInventoryAssets({ search: assetId.trim(), page_size: 1 });
      const match = asset.items[0];
      if (match) {
        setInventoryLabels((current) => ({
          ...current,
          [match.id]: match.display_id ?? match.system_code,
        }));
      }
    } catch {
      setActionError(t('errors.linkInventoryFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  const primaryProjectByOpp = useMemo(() => {
    const map: Record<string, string> = {};
    for (const [oppId, ids] of Object.entries(linkedProjects)) {
      if (ids[0]) map[oppId] = ids[0];
    }
    return map;
  }, [linkedProjects]);

  const primaryInventoryByOpp = useMemo(() => {
    const map: Record<string, string> = {};
    for (const [oppId, ids] of Object.entries(linkedInventory)) {
      if (ids[0]) map[oppId] = ids[0];
    }
    return map;
  }, [linkedInventory]);

  if (!canView) {
    return (
      <main className="dashboard sales">
        <ErrorState title={t('noAccessTitle')} message={t('noAccessMessage')} />
      </main>
    );
  }

  return (
    <main className="dashboard sales">
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
      </header>

      <SalesKpiRow
        kpis={kpis}
        loading={kpisLoading}
        activeKpi={activeKpi}
        labels={kpiLabels}
        locale={locale}
        onKpiClick={handleKpiClick}
      />

      <section className="dashboard__panel leads__panel">
        <div className="sales__toolbar">
          <div className="sales__view-switch">
            <button
              type="button"
              className={`leads__button${appliedFilters.view === 'pipeline' ? ' leads__button--primary' : ' leads__button--secondary'}`}
              onClick={() => {
                const next = { ...appliedFilters, view: 'pipeline' as const };
                setFilters(next);
                setAppliedFilters(next);
              }}
              disabled={!canViewPipeline}
            >
              {t('views.pipeline')}
            </button>
            <button
              type="button"
              className={`leads__button${appliedFilters.view === 'list' ? ' leads__button--primary' : ' leads__button--secondary'}`}
              onClick={() => {
                const next = { ...appliedFilters, view: 'list' as const };
                setFilters(next);
                setAppliedFilters(next);
              }}
            >
              {t('views.list')}
            </button>
          </div>
          {canCreate && (
            <Button onClick={() => { setFormMode('create'); setActionError(null); }}>
              {t('createButton')}
            </Button>
          )}
        </div>

        <SalesFilters
          filters={filters}
          users={users}
          onChange={setFilters}
          onApply={handleApplyFilters}
          onReset={handleResetFilters}
        />

        {actionError && <p className="leads__error">{actionError}</p>}
        {toastError && (
          <p className="leads__error" role="alert">
            {toastError}
            <button type="button" className="leads__button leads__button--ghost" onClick={() => setToastError(null)}>
              ×
            </button>
          </p>
        )}

        {error && (
          <ErrorState
            title={t('loadErrorTitle')}
            message={error}
            action={
              <button type="button" className="leads__button leads__button--secondary" onClick={() => void refreshAll()}>
                {tCommon('retry')}
              </button>
            }
          />
        )}

        {!error && appliedFilters.view === 'pipeline' && canViewPipeline && (
          loading && opportunities.length === 0 ? (
            <LoadingState label={tCommon('loading')} />
          ) : opportunities.length === 0 ? (
            <EmptyState title={t('empty')} description={t('emptyHint')} />
          ) : (
            <SalesPipelineKanban
              opportunities={opportunities}
              partyNames={partyNames}
              userNames={userNames}
              projectNames={Object.fromEntries(projects.map((p) => [p.id, p.project_name]))}
              inventoryLabels={inventoryLabels}
              primaryProjectByOpp={primaryProjectByOpp}
              primaryInventoryByOpp={primaryInventoryByOpp}
              canChangeStage={canChangeStage}
              onOpen={handleOpenOpportunity}
              onStageChange={handleKanbanStageChange}
              onStageChangeError={setToastError}
            />
          )
        )}

        {!error && (appliedFilters.view === 'list' || !canViewPipeline) && (
          <SalesOpportunityTable
            opportunities={opportunities}
            total={total}
            page={appliedFilters.page}
            pageSize={appliedFilters.page_size}
            loading={loading}
            density={density}
            partyNames={partyNames}
            userNames={userNames}
            projectNames={Object.fromEntries(projects.map((p) => [p.id, p.project_name]))}
            primaryProjectByOpp={primaryProjectByOpp}
            sortBy={appliedFilters.sort_by}
            sortDir={appliedFilters.sort_dir}
            onSort={(column) => {
              const nextDir =
                appliedFilters.sort_by === column && appliedFilters.sort_dir === 'desc' ? 'asc' : 'desc';
              const next = { ...appliedFilters, sort_by: column, sort_dir: nextDir as 'asc' | 'desc', page: 1 };
              setFilters(next);
              setAppliedFilters(next);
            }}
            onPageChange={(page) => {
              const next = { ...appliedFilters, page };
              setFilters(next);
              setAppliedFilters(next);
            }}
            onDensityChange={setDensity}
            onOpen={handleOpenOpportunity}
          />
        )}
      </section>

      {selectedOpportunity && (
        <SalesDetailDrawer
          opportunity={selectedOpportunity}
          projects={projects}
          linkedProjectIds={linkedProjects[selectedOpportunity.id] ?? []}
          linkedInventoryIds={linkedInventory[selectedOpportunity.id] ?? []}
          partyName={partyNames[selectedOpportunity.party_id] ?? null}
          assigneeName={
            selectedOpportunity.assigned_sales_user_id
              ? userNames[selectedOpportunity.assigned_sales_user_id] ?? null
              : null
          }
          archiving={submitting}
          canUpdate={canUpdate}
          canChangeStage={canChangeStage}
          canChangeProbability={user ? hasPermission(user, 'sales', 'change_probability') : false}
          canArchive={canArchive}
          canRestore={canRestore}
          canViewSensitiveValue={canViewSensitiveValue || Boolean(selectedOpportunity.expected_revenue)}
          onClose={() => setSelectedOpportunity(null)}
          onEdit={(opp) => { setFormMode('edit'); setSelectedOpportunity(opp); }}
          onArchive={handleArchive}
          onRestore={handleRestore}
          onChangeStage={(opp) => setStageModal({ opportunity: opp, stage: null })}
          onEditNextAction={setNextActionModal}
          onLinkProject={handleLinkProject}
          onLinkInventory={handleLinkInventory}
        />
      )}

      {formMode && (
        <SalesFormModal
          mode={formMode}
          initialLeadId={createLeadId}
          initialPartyId={createLeadId ?? undefined}
          initialPartyType="lead"
          initialValues={
            formMode === 'edit' && selectedOpportunity
              ? {
                  assigned_sales_user_id: selectedOpportunity.assigned_sales_user_id,
                  probability: selectedOpportunity.probability,
                  expected_close_date: selectedOpportunity.expected_close_date,
                  expected_revenue: selectedOpportunity.expected_revenue
                    ? Number(selectedOpportunity.expected_revenue)
                    : null,
                  currency: selectedOpportunity.currency,
                  priority: selectedOpportunity.priority,
                  source: selectedOpportunity.source,
                  next_action: selectedOpportunity.next_action,
                  next_action_date: selectedOpportunity.next_action_date,
                  notes: selectedOpportunity.notes,
                }
              : undefined
          }
          users={users}
          submitting={submitting}
          onClose={() => { setFormMode(null); setCreateLeadId(null); }}
          onSubmit={handleSubmitOpportunity}
        />
      )}

      {stageModal && (
        <SalesStageChangeModal
          opportunity={stageModal.opportunity}
          targetStage={stageModal.stage}
          submitting={submitting}
          onClose={() => setStageModal(null)}
          onSubmit={(payload) => void handleStageChangeRequest(stageModal.opportunity, payload.stage, payload)}
        />
      )}

      {nextActionModal && (
        <SalesNextActionModal
          opportunity={nextActionModal}
          submitting={submitting}
          onClose={() => setNextActionModal(null)}
          onSubmit={(action, date) => void handleNextActionSave(action, date)}
        />
      )}
    </main>
  );
}
