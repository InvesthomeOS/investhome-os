'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';

import { Button, FilterBar, SearchInput, Select } from '@investhome/ui';

import type { Building, Floor, InventoryAssetFilters } from '@/lib/api/inventory';
import type { Project } from '@/lib/api/projects';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

export type InventoryNavView = 'all' | 'by_project' | 'by_building' | 'by_floor';

export interface InventoryFilterState extends InventoryAssetFilters {
  nav_view: InventoryNavView;
}

interface InventoryFiltersProps {
  filters: InventoryFilterState;
  projects: Project[];
  buildings: Building[];
  floors: Floor[];
  onChange: (next: InventoryFilterState) => void;
  onApply: () => void;
  onReset: () => void;
}

function renderOptions(options: { value: string; label: string }[]) {
  return options.map((option) => (
    <option key={option.value || '__empty'} value={option.value}>
      {option.label}
    </option>
  ));
}

export function InventoryFilters({
  filters,
  projects,
  buildings,
  floors,
  onChange,
  onApply,
  onReset,
}: InventoryFiltersProps) {
  const t = useTranslations('inventory');
  const {
    assetTypeOptions,
    availabilityOptions,
    reservationOptions,
    salesOptions,
    constructionOptions,
    closingOptions,
    leasingOptions,
    usageTypeOptions,
  } = useInventoryLabels();

  const navOptions = useMemo(
    () => [
      { value: 'all', label: t('navViews.all') },
      { value: 'by_project', label: t('navViews.byProject') },
      { value: 'by_building', label: t('navViews.byBuilding') },
      { value: 'by_floor', label: t('navViews.byFloor') },
    ],
    [t],
  );

  const projectOptions = useMemo(
    () => [
      { value: '', label: t('filters.allProjects') },
      ...projects.map((p) => ({ value: p.id, label: p.project_name })),
    ],
    [projects, t],
  );

  const buildingOptions = useMemo(
    () => [
      { value: '', label: t('filters.allBuildings') },
      ...buildings.map((b) => ({ value: b.id, label: `${b.code} — ${b.name}` })),
    ],
    [buildings, t],
  );

  const floorOptions = useMemo(
    () => [
      { value: '', label: t('filters.allFloors') },
      ...floors.map((f) => ({
        value: f.id,
        label: f.display_name ?? f.level_code ?? String(f.floor_number),
      })),
    ],
    [floors, t],
  );

  const sortOptions = [
    { value: 'updated_at:desc', label: t('sort.updatedDesc') },
    { value: 'updated_at:asc', label: t('sort.updatedAsc') },
    { value: 'display_id:asc', label: t('sort.displayAsc') },
    { value: 'display_id:desc', label: t('sort.displayDesc') },
    { value: 'system_code:asc', label: t('sort.systemAsc') },
    { value: 'system_code:desc', label: t('sort.systemDesc') },
  ];

  const sortValue = `${filters.sort_by ?? 'updated_at'}:${filters.sort_order ?? 'desc'}`;

  const activeChips = useMemo(() => {
    const chips: { key: string; label: string }[] = [];
    if (filters.search?.trim()) chips.push({ key: 'search', label: `"${filters.search.trim()}"` });
    if (filters.project_id) {
      const project = projects.find((p) => p.id === filters.project_id);
      if (project) chips.push({ key: 'project_id', label: project.project_name });
    }
    if (filters.building_id) {
      const building = buildings.find((b) => b.id === filters.building_id);
      if (building) chips.push({ key: 'building_id', label: building.code });
    }
    if (filters.floor_id) {
      const floor = floors.find((f) => f.id === filters.floor_id);
      if (floor) {
        chips.push({
          key: 'floor_id',
          label: floor.display_name ?? floor.level_code ?? String(floor.floor_number),
        });
      }
    }
    if (filters.asset_type) chips.push({ key: 'asset_type', label: filters.asset_type });
    if (filters.availability_status) {
      chips.push({ key: 'availability_status', label: filters.availability_status });
    }
    if (filters.reservation_status) {
      chips.push({ key: 'reservation_status', label: filters.reservation_status });
    }
    if (filters.sales_status) chips.push({ key: 'sales_status', label: filters.sales_status });
    if (filters.construction_status) {
      chips.push({ key: 'construction_status', label: filters.construction_status });
    }
    if (filters.closing_status) chips.push({ key: 'closing_status', label: filters.closing_status });
    if (filters.leasing_status) chips.push({ key: 'leasing_status', label: filters.leasing_status });
    if (filters.include_archived) chips.push({ key: 'include_archived', label: t('filters.archived') });
    return chips;
  }, [filters, projects, buildings, floors, t]);

  const clearChip = (key: string) => {
    const next = { ...filters };
    if (key === 'search') next.search = '';
    else if (key === 'include_archived') next.include_archived = false;
    else if (key === 'project_id') next.project_id = '';
    else if (key === 'building_id') next.building_id = '';
    else if (key === 'floor_id') next.floor_id = '';
    else if (key === 'asset_type') next.asset_type = '';
    else if (key === 'availability_status') next.availability_status = '';
    else if (key === 'reservation_status') next.reservation_status = '';
    else if (key === 'sales_status') next.sales_status = '';
    else if (key === 'construction_status') next.construction_status = '';
    else if (key === 'closing_status') next.closing_status = '';
    else if (key === 'leasing_status') next.leasing_status = '';
    onChange(next);
    onApply();
  };

  const showProject = filters.nav_view !== 'all';
  const showBuilding = filters.nav_view === 'by_building' || filters.nav_view === 'by_floor';
  const showFloor = filters.nav_view === 'by_floor';

  return (
    <div className="inventory__filters">
      <FilterBar
        actions={
          <>
            <Button variant="secondary" onClick={onApply}>
              {t('filters.apply')}
            </Button>
            <Button variant="ghost" onClick={onReset}>
              {t('filters.clearAll')}
            </Button>
          </>
        }
      >
        <Select
          label={t('navViews.label')}
          value={filters.nav_view}
          onChange={(event) => {
            const navView = event.target.value as InventoryNavView;
            onChange({
              ...filters,
              nav_view: navView,
              project_id: navView === 'all' ? '' : filters.project_id,
              building_id:
                navView === 'by_floor' || navView === 'by_building' ? filters.building_id : '',
              floor_id: navView === 'by_floor' ? filters.floor_id : '',
            });
          }}
        >
          {renderOptions(navOptions)}
        </Select>
        {showProject && (
          <Select
            label={t('filters.project')}
            value={filters.project_id ?? ''}
            onChange={(event) =>
              onChange({ ...filters, project_id: event.target.value, building_id: '', floor_id: '' })
            }
          >
            {renderOptions(projectOptions)}
          </Select>
        )}
        {showBuilding && (
          <Select
            label={t('filters.building')}
            value={filters.building_id ?? ''}
            onChange={(event) =>
              onChange({ ...filters, building_id: event.target.value, floor_id: '' })
            }
            disabled={!filters.project_id}
          >
            {renderOptions(buildingOptions)}
          </Select>
        )}
        {showFloor && (
          <Select
            label={t('filters.floor')}
            value={filters.floor_id ?? ''}
            onChange={(event) => onChange({ ...filters, floor_id: event.target.value })}
            disabled={!filters.building_id}
          >
            {renderOptions(floorOptions)}
          </Select>
        )}
        <SearchInput
          label={t('filters.search')}
          value={filters.search ?? ''}
          placeholder={t('filters.searchPlaceholder')}
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
        />
        <Select
          label={t('filters.assetType')}
          value={filters.asset_type ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              asset_type: event.target.value as InventoryAssetFilters['asset_type'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allTypes') }, ...assetTypeOptions])}
        </Select>
        <Select
          label={t('filters.usageType')}
          value={filters.usage_type ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              usage_type: event.target.value as InventoryAssetFilters['usage_type'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allUsage') }, ...usageTypeOptions])}
        </Select>
        <Select
          label={t('filters.availability')}
          value={filters.availability_status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              availability_status: event.target.value as InventoryAssetFilters['availability_status'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allStatuses') }, ...availabilityOptions])}
        </Select>
        <Select
          label={t('filters.reservation')}
          value={filters.reservation_status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              reservation_status: event.target.value as InventoryAssetFilters['reservation_status'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allStatuses') }, ...reservationOptions])}
        </Select>
        <Select
          label={t('filters.sales')}
          value={filters.sales_status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              sales_status: event.target.value as InventoryAssetFilters['sales_status'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allStatuses') }, ...salesOptions])}
        </Select>
        <Select
          label={t('filters.construction')}
          value={filters.construction_status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              construction_status: event.target.value as InventoryAssetFilters['construction_status'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allStatuses') }, ...constructionOptions])}
        </Select>
        <Select
          label={t('filters.closing')}
          value={filters.closing_status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              closing_status: event.target.value as InventoryAssetFilters['closing_status'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allStatuses') }, ...closingOptions])}
        </Select>
        <Select
          label={t('filters.leasing')}
          value={filters.leasing_status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              leasing_status: event.target.value as InventoryAssetFilters['leasing_status'],
            })
          }
        >
          {renderOptions([{ value: '', label: t('filters.allStatuses') }, ...leasingOptions])}
        </Select>
        <Select
          label={t('filters.sort')}
          value={sortValue}
          onChange={(event) => {
            const [sort_by, sort_order] = event.target.value.split(':') as [string, 'asc' | 'desc'];
            onChange({ ...filters, sort_by, sort_order });
          }}
        >
          {renderOptions(sortOptions)}
        </Select>
        <label className="ih-field inventory__checkbox-field">
          <span className="ih-field__label">{t('filters.includeArchived')}</span>
          <input
            type="checkbox"
            checked={Boolean(filters.include_archived)}
            onChange={(event) => onChange({ ...filters, include_archived: event.target.checked })}
          />
        </label>
      </FilterBar>

      {activeChips.length > 0 && (
        <div className="inventory__filter-chips" role="list" aria-label={t('filters.activeChips')}>
          {activeChips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              className="inventory__filter-chip"
              onClick={() => clearChip(chip.key)}
              role="listitem"
            >
              {chip.label} ×
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
