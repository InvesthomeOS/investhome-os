'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  Button,
  EmptyState,
  ErrorState,
  LoadingState,
  Pagination,
  StatusChip,
  Table,
  TableToolbar,
} from '@investhome/ui';

import {
  archiveInventoryAsset,
  createInventoryAsset,
  fetchBuildings,
  fetchFloors,
  fetchInventoryAsset,
  fetchInventoryAssets,
  fetchInventoryKpis,
  formatArea,
  formatDateTime,
  getAreaDisplayUnit,
  isParkingAsset,
  isStorageAsset,
  restoreInventoryAsset,
  updateInventoryAsset,
  updateInventoryAssetStatus,
  type Building,
  type Floor,
  type InventoryAsset,
  type InventoryAssetInput,
  type InventoryKpis,
  type StatusUpdateInput,
} from '@/lib/api/inventory';
import { ApiError } from '@/lib/api/client';
import { hasPermission } from '@/lib/api/auth';
import { fetchProjects, type Project } from '@/lib/api/projects';
import { useAuth } from '@/lib/auth/auth-context';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

import { InventoryCreateModal } from './inventory-create-modal';
import { InventoryDetailDrawer } from './inventory-detail-drawer';
import {
  InventoryFilters,
  type InventoryFilterState,
} from './inventory-filters';
import { InventoryKpiRow, type InventoryKpiKey } from './inventory-kpi-row';
import { StatusUpdateModal } from './status-update-modal';

const FILTER_STORAGE_KEY = 'investhome.inventory.filters';
const PAGE_SIZE = 20;

type FormMode = 'create' | 'edit' | null;
type TableDensity = 'comfortable' | 'compact';

const EMPTY_FILTERS: InventoryFilterState = {
  nav_view: 'all',
  search: '',
  project_id: '',
  building_id: '',
  floor_id: '',
  asset_type: '',
  usage_type: '',
  availability_status: '',
  reservation_status: '',
  sales_status: '',
  construction_status: '',
  closing_status: '',
  leasing_status: '',
  include_archived: false,
  sort_by: 'updated_at',
  sort_order: 'desc',
  page: 1,
  page_size: PAGE_SIZE,
};

function loadStoredFilters(): InventoryFilterState {
  if (typeof window === 'undefined') return EMPTY_FILTERS;
  try {
    const raw = sessionStorage.getItem(FILTER_STORAGE_KEY);
    if (!raw) return EMPTY_FILTERS;
    return { ...EMPTY_FILTERS, ...JSON.parse(raw) };
  } catch {
    return EMPTY_FILTERS;
  }
}

function kpiToFilter(key: InventoryKpiKey): Partial<InventoryFilterState> {
  const cleared = {
    availability_status: '' as const,
    reservation_status: '' as const,
    sales_status: '' as const,
    closing_status: '' as const,
    leasing_status: '' as const,
  };
  switch (key) {
    case 'available':
      return { ...cleared, availability_status: 'available' };
    case 'soft_hold':
      return { ...cleared, reservation_status: 'soft_hold' };
    case 'reserved':
      return { ...cleared, reservation_status: 'confirmed' };
    case 'under_contract':
      return { ...cleared, sales_status: 'under_contract' };
    case 'sold':
      return { ...cleared, sales_status: 'sold' };
    case 'closed':
      return { ...cleared, closing_status: 'closed' };
    case 'leased':
      return { ...cleared, leasing_status: 'leased' };
    default:
      return cleared;
  }
}

function assetTypeIcon(asset: InventoryAsset): string {
  if (isParkingAsset(asset.asset_type)) return 'P';
  if (isStorageAsset(asset.asset_type)) return 'S';
  return 'U';
}

export function InventoryWorkspace() {
  const t = useTranslations('inventory');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const areaUnit = getAreaDisplayUnit();
  const {
    getAssetTypeLabel,
    getAvailabilityLabel,
    getReservationLabel,
    getSalesLabel,
    getConstructionLabel,
    getClosingLabel,
    getLeasingLabel,
    getErrorLabel,
  } = useInventoryLabels();

  const canCreate = user ? hasPermission(user, 'inventory', 'create') : false;
  const canUpdate = user ? hasPermission(user, 'inventory', 'update') : false;
  const canArchive = user ? hasPermission(user, 'inventory', 'archive') : false;
  const canRestore = user ? hasPermission(user, 'inventory', 'restore') : false;
  const canManageStatus = user ? hasPermission(user, 'inventory', 'manage_status') : false;

  const [assets, setAssets] = useState<InventoryAsset[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [formBuildings, setFormBuildings] = useState<Building[]>([]);
  const [formFloors, setFormFloors] = useState<Floor[]>([]);
  const [kpis, setKpis] = useState<InventoryKpis | null>(null);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [filters, setFilters] = useState<InventoryFilterState>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<InventoryFilterState>(EMPTY_FILTERS);
  const [activeKpi, setActiveKpi] = useState<InventoryKpiKey | null>(null);
  const [loading, setLoading] = useState(true);
  const [kpiLoading, setKpiLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<InventoryAsset | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [statusModalOpen, setStatusModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [density, setDensity] = useState<TableDensity>('comfortable');

  const projectMap = useMemo(
    () => new Map(projects.map((project) => [project.id, project.project_name])),
    [projects],
  );
  const buildingMap = useMemo(
    () => new Map(buildings.map((building) => [building.id, building.code])),
    [buildings],
  );
  const floorMap = useMemo(
    () =>
      new Map(
        floors.map((floor) => [
          floor.id,
          floor.display_name ?? floor.level_code ?? String(floor.floor_number),
        ]),
      ),
    [floors],
  );

  const kpiLabels: Record<InventoryKpiKey, string> = useMemo(
    () => ({
      total: t('kpis.total'),
      available: t('kpis.available'),
      soft_hold: t('kpis.softHold'),
      reserved: t('kpis.reserved'),
      under_contract: t('kpis.underContract'),
      sold: t('kpis.sold'),
      closed: t('kpis.closed'),
      leased: t('kpis.leased'),
    }),
    [t],
  );

  const persistFilters = useCallback((next: InventoryFilterState) => {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem(FILTER_STORAGE_KEY, JSON.stringify(next));
  }, []);

  useEffect(() => {
    const stored = loadStoredFilters();
    setFilters(stored);
    setAppliedFilters(stored);
  }, []);

  const loadProjects = useCallback(async () => {
    try {
      const response = await fetchProjects({ page_size: 100, sort_by: 'project_name', sort_order: 'asc' });
      setProjects(response.items);
    } catch {
      setProjects([]);
    }
  }, []);

  const loadBuildings = useCallback(async (projectId?: string) => {
    try {
      const response = await fetchBuildings({
        project_id: projectId || undefined,
        page_size: 100,
        sort_by: 'code',
        sort_order: 'asc',
      });
      setBuildings(response.items);
    } catch {
      setBuildings([]);
    }
  }, []);

  const loadFloors = useCallback(async (buildingId?: string, projectId?: string) => {
    try {
      const response = await fetchFloors({
        building_id: buildingId || undefined,
        project_id: buildingId ? undefined : projectId || undefined,
        page_size: 100,
        sort_by: 'sort_order',
        sort_order: 'asc',
      });
      setFloors(response.items);
    } catch {
      setFloors([]);
    }
  }, []);

  const loadKpis = useCallback(async (scope: Pick<InventoryFilterState, 'project_id' | 'building_id' | 'floor_id'>) => {
    setKpiLoading(true);
    try {
      const response = await fetchInventoryKpis({
        project_id: scope.project_id || undefined,
        building_id: scope.building_id || undefined,
        floor_id: scope.floor_id || undefined,
      });
      setKpis(response);
    } catch {
      setKpis(null);
    } finally {
      setKpiLoading(false);
    }
  }, []);

  const loadAssets = useCallback(
    async (nextFilters: InventoryFilterState) => {
      setLoading(true);
      setError(null);
      try {
        const { nav_view, ...apiFilters } = nextFilters;
        const response = await fetchInventoryAssets(apiFilters);
        setAssets(response.items);
        setTotal(response.total);
        setPages(response.pages);
      } catch {
        setError(t('loadError'));
        setAssets([]);
        setTotal(0);
        setPages(0);
      } finally {
        setLoading(false);
      }
    },
    [t],
  );

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    void loadBuildings(appliedFilters.project_id || undefined);
    void loadFloors(appliedFilters.building_id || undefined, appliedFilters.project_id || undefined);
  }, [appliedFilters.project_id, appliedFilters.building_id, loadBuildings, loadFloors]);

  useEffect(() => {
    void loadAssets(appliedFilters);
    void loadKpis(appliedFilters);
    persistFilters(appliedFilters);
  }, [appliedFilters, loadAssets, loadKpis, persistFilters]);

  const handleOpenAsset = useCallback((asset: InventoryAsset) => setSelectedAsset(asset), []);
  useRecordDeepLink(fetchInventoryAsset, handleOpenAsset);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadAssets(appliedFilters), loadKpis(appliedFilters)]);
  }, [appliedFilters, loadAssets, loadKpis]);

  const handleApplyFilters = () => {
    setAppliedFilters({ ...filters, page: 1 });
  };

  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setActiveKpi(null);
  };

  const handleKpiClick = (key: InventoryKpiKey) => {
    const nextActive = activeKpi === key ? null : key;
    setActiveKpi(nextActive);
    const statusFilters = nextActive ? kpiToFilter(nextActive) : kpiToFilter('total');
    const next = { ...appliedFilters, ...statusFilters, page: 1 };
    setFilters(next);
    setAppliedFilters(next);
  };

  const handlePageChange = (page: number) => {
    setAppliedFilters((current) => ({ ...current, page }));
  };

  const handleFormProjectChange = async (projectId: string) => {
    if (!projectId) {
      setFormBuildings([]);
      setFormFloors([]);
      return;
    }
    const response = await fetchBuildings({ project_id: projectId, page_size: 100 });
    setFormBuildings(response.items);
    setFormFloors([]);
  };

  const handleFormBuildingChange = async (buildingId: string) => {
    if (!buildingId) {
      setFormFloors([]);
      return;
    }
    const response = await fetchFloors({ building_id: buildingId, page_size: 100 });
    setFormFloors(response.items);
  };

  const parseActionError = (err: unknown): string => {
    if (err instanceof ApiError) {
      return getErrorLabel(err.message);
    }
    return t('saveError');
  };

  const handleSubmitAsset = async (input: InventoryAssetInput) => {
    setSubmitting(true);
    setActionError(null);
    try {
      if (formMode === 'create') {
        const created = await createInventoryAsset(input);
        setSelectedAsset(created);
      } else if (formMode === 'edit' && selectedAsset) {
        const updated = await updateInventoryAsset(selectedAsset.id, input);
        setSelectedAsset(updated);
      }
      setFormMode(null);
      await refreshAll();
    } catch (err) {
      setActionError(parseActionError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleArchiveAsset = async (asset: InventoryAsset) => {
    setSubmitting(true);
    setActionError(null);
    try {
      await archiveInventoryAsset(asset.id);
      setSelectedAsset(null);
      await refreshAll();
    } catch {
      setActionError(t('archiveError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleRestoreAsset = async (asset: InventoryAsset) => {
    setSubmitting(true);
    setActionError(null);
    try {
      const restored = await restoreInventoryAsset(asset.id);
      setSelectedAsset(restored);
      await refreshAll();
    } catch {
      setActionError(t('restoreError'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusSubmit = async (input: StatusUpdateInput) => {
    if (!selectedAsset) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await updateInventoryAssetStatus(selectedAsset.id, input);
      const refreshed = await fetchInventoryAsset(selectedAsset.id);
      setSelectedAsset(refreshed);
      setStatusModalOpen(false);
      await refreshAll();
    } catch (err) {
      setActionError(parseActionError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const demoCount = useMemo(() => assets.filter((asset) => asset.is_demo).length, [assets]);

  const tableClass = density === 'compact' ? 'ih-table ih-table--compact admin-table' : 'ih-table admin-table';

  return (
    <main className="dashboard inventory">
      <header className="dashboard__header leads__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="leads__subtitle">{t('subtitle')}</p>
      </header>

      <InventoryKpiRow
        kpis={kpis}
        loading={kpiLoading}
        activeKpi={activeKpi}
        labels={kpiLabels}
        onKpiClick={handleKpiClick}
      />

      {demoCount > 0 && (
        <div className="leads__demo-banner" role="status">
          {t('demoBanner', { count: demoCount })}
        </div>
      )}

      <section className="dashboard__panel inventory__panel">
        <TableToolbar
          actions={
            <>
              <Button
                variant="ghost"
                onClick={() => setDensity((current) => (current === 'comfortable' ? 'compact' : 'comfortable'))}
              >
                {density === 'comfortable' ? t('table.compact') : t('table.comfortable')}
              </Button>
              {canCreate && (
                <Button variant="primary" onClick={() => { setActionError(null); setFormMode('create'); }}>
                  {t('createButton')}
                </Button>
              )}
            </>
          }
        >
          <span className="inventory__result-count">
            {t('resultCount', { count: total })}
          </span>
        </TableToolbar>

        <InventoryFilters
          filters={filters}
          projects={projects}
          buildings={buildings}
          floors={floors}
          onChange={setFilters}
          onApply={handleApplyFilters}
          onReset={handleResetFilters}
        />

        {actionError && <p className="leads__state leads__state--error">{actionError}</p>}

        {loading && <LoadingState label={tCommon('loading')} />}
        {!loading && error && (
          <ErrorState
            title={t('loadErrorTitle')}
            message={error}
            action={
              <Button variant="secondary" onClick={() => void loadAssets(appliedFilters)}>
                {tCommon('retry')}
              </Button>
            }
          />
        )}
        {!loading && !error && assets.length === 0 && (
          <EmptyState title={t('empty')} description={t('emptyHint')} />
        )}

        {!loading && !error && assets.length > 0 && (
          <>
            <Table className={tableClass}>
              <thead>
                <tr>
                  <th aria-hidden="true" />
                  <th>{t('columns.displayId')}</th>
                  <th>{t('columns.systemCode')}</th>
                  <th>{t('columns.legalIdentifier')}</th>
                  <th>{t('columns.assetType')}</th>
                  <th>{t('columns.project')}</th>
                  <th>{t('columns.building')}</th>
                  <th>{t('columns.floor')}</th>
                  <th>{t('columns.interiorArea')}</th>
                  <th>{t('columns.availability')}</th>
                  <th>{t('columns.reservation')}</th>
                  <th>{t('columns.sales')}</th>
                  <th>{t('columns.construction')}</th>
                  <th>{t('columns.closing')}</th>
                  <th>{t('columns.leasing')}</th>
                  <th>{t('columns.updated')}</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => {
                  const isSelected = selectedAsset?.id === asset.id;
                  return (
                    <tr
                      key={asset.id}
                      className={`leads__row inventory__row${isSelected ? ' inventory__row--selected' : ''}`}
                      onClick={() => setSelectedAsset(asset)}
                    >
                      <td>
                        <span className="inventory__asset-icon" title={getAssetTypeLabel(asset.asset_type)}>
                          {assetTypeIcon(asset)}
                        </span>
                      </td>
                      <td>{asset.display_id}</td>
                      <td>{asset.system_code}</td>
                      <td>{asset.legal_identifier ?? '—'}</td>
                      <td>{getAssetTypeLabel(asset.asset_type)}</td>
                      <td>{projectMap.get(asset.project_id) ?? '—'}</td>
                      <td>{asset.building_id ? buildingMap.get(asset.building_id) ?? '—' : '—'}</td>
                      <td>{asset.floor_id ? floorMap.get(asset.floor_id) ?? '—' : '—'}</td>
                      <td className="ih-table__numeric">
                        {formatArea(asset.interior_area_sqft, locale, areaUnit)}
                      </td>
                      <td>
                        <StatusChip tone="info">{getAvailabilityLabel(asset.availability_status)}</StatusChip>
                      </td>
                      <td>
                        <StatusChip>{getReservationLabel(asset.reservation_status)}</StatusChip>
                      </td>
                      <td>
                        <StatusChip>{getSalesLabel(asset.sales_status)}</StatusChip>
                      </td>
                      <td>
                        <StatusChip>{getConstructionLabel(asset.construction_status)}</StatusChip>
                      </td>
                      <td>
                        <StatusChip>{getClosingLabel(asset.closing_status)}</StatusChip>
                      </td>
                      <td>
                        <StatusChip>{getLeasingLabel(asset.leasing_status)}</StatusChip>
                      </td>
                      <td>{formatDateTime(asset.updated_at, locale)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </Table>

            <Pagination
              page={appliedFilters.page ?? 1}
              pageSize={appliedFilters.page_size ?? PAGE_SIZE}
              total={total}
              onPrevious={() => handlePageChange((appliedFilters.page ?? 1) - 1)}
              onNext={() => handlePageChange((appliedFilters.page ?? 1) + 1)}
              previousLabel={t('prevPage')}
              nextLabel={t('nextPage')}
              summary={t('pagination', { page: appliedFilters.page ?? 1, pages, total })}
            />
          </>
        )}
      </section>

      <InventoryDetailDrawer
        asset={selectedAsset}
        projects={projects}
        buildings={buildings}
        floors={floors}
        archiving={submitting}
        canManageStatus={canManageStatus}
        canUpdate={canUpdate}
        canArchive={canArchive}
        canRestore={canRestore}
        onClose={() => setSelectedAsset(null)}
        onEdit={(asset) => { setActionError(null); setSelectedAsset(asset); setFormMode('edit'); }}
        onArchive={handleArchiveAsset}
        onRestore={handleRestoreAsset}
        onStatusUpdate={() => { setActionError(null); setStatusModalOpen(true); }}
      />

      <InventoryCreateModal
        mode={formMode}
        asset={selectedAsset}
        projects={projects}
        buildings={formBuildings}
        floors={formFloors}
        submitting={submitting}
        error={actionError}
        onClose={() => setFormMode(null)}
        onSubmit={handleSubmitAsset}
        onProjectChange={(projectId) => void handleFormProjectChange(projectId)}
        onBuildingChange={(buildingId) => void handleFormBuildingChange(buildingId)}
      />

      <StatusUpdateModal
        asset={selectedAsset}
        open={statusModalOpen}
        submitting={submitting}
        error={actionError}
        onClose={() => setStatusModalOpen(false)}
        onSubmit={handleStatusSubmit}
      />
    </main>
  );
}
