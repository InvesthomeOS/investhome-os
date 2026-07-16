'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, Drawer, StatusChip, Tabs } from '@investhome/ui';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import {
  fetchInventoryAssetStatusHistory,
  formatArea,
  formatDateTime,
  formatShortDate,
  getAreaDisplayUnit,
  isParkingAsset,
  isStorageAsset,
  type Building,
  type Floor,
  type InventoryAsset,
  type InventoryAssetStatusHistory,
} from '@/lib/api/inventory';
import type { Project } from '@/lib/api/projects';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

type DetailTab =
  | 'overview'
  | 'status'
  | 'physical'
  | 'assignments'
  | 'dates'
  | 'documents'
  | 'drawings'
  | 'design'
  | 'activity'
  | 'statusHistory';

interface InventoryDetailDrawerProps {
  asset: InventoryAsset | null;
  projects: Project[];
  buildings: Building[];
  floors: Floor[];
  archiving: boolean;
  canManageStatus: boolean;
  canUpdate: boolean;
  canArchive: boolean;
  canRestore: boolean;
  onClose: () => void;
  onEdit: (asset: InventoryAsset) => void;
  onArchive: (asset: InventoryAsset) => void;
  onRestore: (asset: InventoryAsset) => void;
  onStatusUpdate: (asset: InventoryAsset) => void;
}

function DetailField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="leads-drawer__section">
      <h3>{title}</h3>
      <dl className="leads-drawer__grid">{children}</dl>
    </section>
  );
}

function assetTypeIcon(asset: InventoryAsset): string {
  if (isParkingAsset(asset.asset_type)) return 'P';
  if (isStorageAsset(asset.asset_type)) return 'S';
  return 'U';
}

export function InventoryDetailDrawer({
  asset,
  projects,
  buildings,
  floors,
  archiving,
  canManageStatus,
  canUpdate,
  canArchive,
  canRestore,
  onClose,
  onEdit,
  onArchive,
  onRestore,
  onStatusUpdate,
}: InventoryDetailDrawerProps) {
  const t = useTranslations('inventory');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const areaUnit = getAreaDisplayUnit();
  const {
    getAssetTypeLabel,
    getUsageTypeLabel,
    getAvailabilityLabel,
    getReservationLabel,
    getSalesLabel,
    getConstructionLabel,
    getClosingLabel,
    getLeasingLabel,
    getStatusCategoryLabel,
  } = useInventoryLabels();

  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [statusHistory, setStatusHistory] = useState<InventoryAssetStatusHistory[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const canViewDocuments = user ? hasPermission(user, 'documents', 'view') : false;
  const canViewDesign = user ? hasPermission(user, 'design', 'view') : false;
  const canViewActivity = user ? hasPermission(user, 'activity', 'view') : false;

  const project = useMemo(
    () => (asset ? projects.find((p) => p.id === asset.project_id) : undefined),
    [asset, projects],
  );
  const building = useMemo(
    () => (asset?.building_id ? buildings.find((b) => b.id === asset.building_id) : undefined),
    [asset, buildings],
  );
  const floor = useMemo(
    () => (asset?.floor_id ? floors.find((f) => f.id === asset.floor_id) : undefined),
    [asset, floors],
  );

  const loadHistory = useCallback(async () => {
    if (!asset) return;
    setHistoryLoading(true);
    try {
      const rows = await fetchInventoryAssetStatusHistory(asset.id);
      setStatusHistory(rows);
    } catch {
      setStatusHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  }, [asset]);

  useEffect(() => {
    if (asset && (activeTab === 'statusHistory' || activeTab === 'status')) {
      void loadHistory();
    }
  }, [asset, activeTab, loadHistory]);

  if (!asset) return null;

  const tabs = [
    { id: 'overview', label: t('detail.tabs.overview') },
    { id: 'status', label: t('detail.tabs.status') },
    { id: 'physical', label: t('detail.tabs.physical') },
    { id: 'assignments', label: t('detail.tabs.assignments') },
    { id: 'dates', label: t('detail.tabs.dates') },
    ...(canViewDocuments ? [{ id: 'documents', label: t('detail.tabs.documents') }] : []),
    { id: 'drawings', label: t('detail.tabs.drawings') },
    ...(canViewDesign ? [{ id: 'design', label: t('detail.tabs.design') }] : []),
    ...(canViewActivity ? [{ id: 'activity', label: t('detail.tabs.activity') }] : []),
    { id: 'statusHistory', label: t('detail.tabs.statusHistory') },
  ];

  const getStatusLabelForHistory = (category: string, value: string) => {
    switch (category) {
      case 'availability':
        return getAvailabilityLabel(value);
      case 'reservation':
        return getReservationLabel(value);
      case 'sales':
        return getSalesLabel(value);
      case 'construction':
        return getConstructionLabel(value);
      case 'closing':
        return getClosingLabel(value);
      case 'leasing':
        return getLeasingLabel(value);
      default:
        return value;
    }
  };

  return (
    <Drawer
      open
      onClose={onClose}
      wide
      title={asset.display_id}
      ariaLabel={t('detail.ariaLabel')}
      footer={
        <div className="inventory__drawer-actions">
          {canUpdate && (
            <Button variant="secondary" onClick={() => onEdit(asset)}>
              {tCommon('edit')}
            </Button>
          )}
          {canManageStatus && (
            <Button variant="secondary" onClick={() => onStatusUpdate(asset)}>
              {t('detail.changeStatus')}
            </Button>
          )}
          {canArchive && !asset.archived_at && (
            <Button variant="danger" onClick={() => onArchive(asset)} disabled={archiving}>
              {archiving ? tCommon('saving') : t('detail.archive')}
            </Button>
          )}
          {canRestore && asset.archived_at && (
            <Button variant="secondary" onClick={() => onRestore(asset)} disabled={archiving}>
              {archiving ? tCommon('saving') : t('detail.restore')}
            </Button>
          )}
        </div>
      }
    >
      <div className="inventory__drawer-header-meta">
        <span className="inventory__asset-icon" aria-hidden="true">
          {assetTypeIcon(asset)}
        </span>
        <div>
          <p className="leads__meta">{asset.system_code}</p>
          <p className="leads__meta">
            {getAssetTypeLabel(asset.asset_type)} · {project?.project_name ?? tCommon('noValue')}
          </p>
          {asset.is_demo && <span className="leads__demo-tag">{tCommon('demoData')}</span>}
          {asset.archived_at && (
            <StatusChip tone="warning">{t('detail.archivedBadge')}</StatusChip>
          )}
        </div>
      </div>

      <Tabs
        tabs={tabs}
        activeId={activeTab}
        onChange={(id) => setActiveTab(id as DetailTab)}
        ariaLabel={t('detail.tabsLabel')}
      />

      {activeTab === 'overview' && (
        <>
          <DetailSection title={t('detail.sections.identifiers')}>
            <DetailField label={t('columns.displayId')} value={asset.display_id} />
            <DetailField label={t('columns.systemCode')} value={asset.system_code} />
            <DetailField
              label={t('columns.legalIdentifier')}
              value={
                asset.legal_identifier ? (
                  <>
                    {asset.legal_identifier} <span aria-hidden="true">🔒</span>
                  </>
                ) : (
                  tCommon('noValue')
                )
              }
            />
            <DetailField label={t('columns.assetType')} value={getAssetTypeLabel(asset.asset_type)} />
            <DetailField label={t('columns.usageType')} value={getUsageTypeLabel(asset.usage_type)} />
          </DetailSection>

          <DetailSection title={t('detail.sections.location')}>
            <DetailField label={t('columns.project')} value={project?.project_name ?? tCommon('noValue')} />
            <DetailField label={t('columns.building')} value={building?.code ?? tCommon('noValue')} />
            <DetailField
              label={t('columns.floor')}
              value={
                floor
                  ? floor.display_name ?? floor.level_code ?? String(floor.floor_number)
                  : tCommon('noValue')
              }
            />
          </DetailSection>

          <DetailSection title={t('detail.sections.statusSummary')}>
            <DetailField
              label={t('columns.availability')}
              value={<StatusChip tone="info">{getAvailabilityLabel(asset.availability_status)}</StatusChip>}
            />
            <DetailField
              label={t('columns.reservation')}
              value={<StatusChip>{getReservationLabel(asset.reservation_status)}</StatusChip>}
            />
            <DetailField
              label={t('columns.sales')}
              value={<StatusChip>{getSalesLabel(asset.sales_status)}</StatusChip>}
            />
            <DetailField
              label={t('columns.construction')}
              value={<StatusChip>{getConstructionLabel(asset.construction_status)}</StatusChip>}
            />
            <DetailField
              label={t('columns.closing')}
              value={<StatusChip>{getClosingLabel(asset.closing_status)}</StatusChip>}
            />
            <DetailField
              label={t('columns.leasing')}
              value={<StatusChip>{getLeasingLabel(asset.leasing_status)}</StatusChip>}
            />
          </DetailSection>

          {asset.description && (
            <DetailSection title={t('detail.sections.description')}>
              <DetailField label={t('form.description')} value={asset.description} />
            </DetailSection>
          )}
        </>
      )}

      {activeTab === 'status' && (
        <DetailSection title={t('detail.sections.currentStatus')}>
          <DetailField label={t('columns.availability')} value={getAvailabilityLabel(asset.availability_status)} />
          <DetailField label={t('columns.reservation')} value={getReservationLabel(asset.reservation_status)} />
          <DetailField label={t('columns.sales')} value={getSalesLabel(asset.sales_status)} />
          <DetailField label={t('columns.construction')} value={getConstructionLabel(asset.construction_status)} />
          <DetailField label={t('columns.closing')} value={getClosingLabel(asset.closing_status)} />
          <DetailField label={t('columns.leasing')} value={getLeasingLabel(asset.leasing_status)} />
          {canManageStatus && (
            <div className="inventory__drawer-inline-action">
              <Button variant="secondary" onClick={() => onStatusUpdate(asset)}>
                {t('detail.changeStatus')}
              </Button>
            </div>
          )}
          {statusHistory.length > 0 && (
            <div className="inventory__history-snippet">
              <h4>{t('detail.recentChanges')}</h4>
              <ul>
                {statusHistory.slice(0, 3).map((row) => (
                  <li key={row.id}>
                    {getStatusCategoryLabel(row.status_category)}:{' '}
                    {row.previous_status
                      ? `${getStatusLabelForHistory(row.status_category, row.previous_status)} → `
                      : ''}
                    {getStatusLabelForHistory(row.status_category, row.new_status)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </DetailSection>
      )}

      {activeTab === 'physical' && (
        <DetailSection title={t('detail.sections.physical')}>
          <DetailField label={t('form.unitSubtype')} value={asset.unit_subtype ?? tCommon('noValue')} />
          <DetailField label={t('form.bedrooms')} value={asset.bedrooms ?? tCommon('noValue')} />
          <DetailField label={t('form.bathrooms')} value={asset.bathrooms ?? tCommon('noValue')} />
          <DetailField
            label={t('columns.interiorArea')}
            value={formatArea(asset.interior_area_sqft, locale, areaUnit)}
          />
          <DetailField
            label={t('columns.exteriorArea')}
            value={formatArea(asset.exterior_area_sqft, locale, areaUnit)}
          />
          <DetailField
            label={t('columns.totalArea')}
            value={formatArea(asset.total_area_sqft, locale, areaUnit)}
          />
          <DetailField label={t('form.orientation')} value={asset.orientation ?? tCommon('noValue')} />
          <DetailField label={t('form.viewType')} value={asset.view_type ?? tCommon('noValue')} />
        </DetailSection>
      )}

      {activeTab === 'assignments' && (
        <section className="leads-drawer__section">
          <p className="leads__state">{t('detail.assignmentsEmpty')}</p>
        </section>
      )}

      {activeTab === 'dates' && (
        <DetailSection title={t('detail.sections.dates')}>
          <DetailField label={t('form.releaseDate')} value={formatShortDate(asset.release_date, locale)} />
          <DetailField label={t('form.deliveryDate')} value={formatShortDate(asset.delivery_date, locale)} />
          <DetailField label={t('columns.updated')} value={formatDateTime(asset.updated_at, locale)} />
          <DetailField label={t('detail.created')} value={formatDateTime(asset.created_at, locale)} />
        </DetailSection>
      )}

      {activeTab === 'documents' && canViewDocuments && (
        <EntityDocumentsPanel entityType="inventory_asset" entityId={asset.id} projectId={asset.project_id} />
      )}

      {activeTab === 'drawings' && (
        <section className="leads-drawer__section">
          <p className="leads__state">{t('detail.drawingsEmpty')}</p>
        </section>
      )}

      {activeTab === 'design' && canViewDesign && (
        <section className="leads-drawer__section">
          <p className="leads__state">{t('detail.designEmpty')}</p>
          <Link href="/dashboard/design" className="leads__button leads__button--secondary">
            {t('detail.openDesignStudio')}
          </Link>
        </section>
      )}

      {activeTab === 'activity' && canViewActivity && (
        <EntityActivityTimeline entityType="inventory_asset" entityId={asset.id} />
      )}

      {activeTab === 'statusHistory' && (
        <section className="leads-drawer__section">
          <h3>{t('detail.tabs.statusHistory')}</h3>
          {historyLoading && <p className="leads__state">{tCommon('loading')}</p>}
          {!historyLoading && statusHistory.length === 0 && (
            <p className="leads__state">{t('detail.statusHistoryEmpty')}</p>
          )}
          {!historyLoading && statusHistory.length > 0 && (
            <ol className="activity-timeline__list">
              {statusHistory.map((row) => (
                <li key={row.id} className="activity-timeline__item">
                  <time className="activity-timeline__time" dateTime={row.effective_at}>
                    {formatDateTime(row.effective_at, locale)}
                  </time>
                  <div className="activity-timeline__body">
                    <p className="activity-timeline__summary">
                      <strong>{getStatusCategoryLabel(row.status_category)}</strong>:{' '}
                      {row.previous_status
                        ? `${getStatusLabelForHistory(row.status_category, row.previous_status)} → `
                        : ''}
                      {getStatusLabelForHistory(row.status_category, row.new_status)}
                    </p>
                    {row.reason && <span className="activity-timeline__actor">{row.reason}</span>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </Drawer>
  );
}
