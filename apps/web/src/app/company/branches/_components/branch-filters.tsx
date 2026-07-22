'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { BranchListParams } from '@/lib/api/branches';

export type BranchFilterState = BranchListParams & {
  showAdvanced: boolean;
};

type BranchFiltersProps = {
  filters: BranchFilterState;
  onChange: (next: BranchFilterState) => void;
  onApply: () => void;
  onClear: () => void;
};

const BRANCH_TYPES = [
  'head_office',
  'regional_office',
  'corporate_office',
  'sales_office',
  'construction_office',
  'project_office',
  'warehouse',
  'service_center',
  'temporary_office',
  'remote_office',
  'other',
] as const;

const BRANCH_STATUSES = [
  'planning',
  'opening_soon',
  'active',
  'inactive',
  'temporarily_closed',
  'closed',
  'archived',
] as const;

export function BranchFilters({ filters, onChange, onApply, onClear }: BranchFiltersProps) {
  const t = useTranslations('company.branches');
  const tTypes = useTranslations('company.branches.types');
  const tStatuses = useTranslations('company.branches.statuses');

  const activeCount = useMemo(() => {
    let count = 0;
    if (filters.search) count += 1;
    if (filters.country) count += 1;
    if (filters.state) count += 1;
    if (filters.city) count += 1;
    if (filters.branch_type) count += 1;
    if (filters.status) count += 1;
    if (filters.include_archived) count += 1;
    return count;
  }, [filters]);

  return (
    <div className="company-filters">
      <div className="company-filters__row">
        <label className="company-filters__field company-filters__field--grow">
          <span>{t('searchLabel')}</span>
          <input
            type="search"
            value={filters.search ?? ''}
            placeholder={t('searchPlaceholder')}
            onChange={(event) => onChange({ ...filters, search: event.target.value, page: 1 })}
          />
        </label>
        <Button type="button" variant="secondary" onClick={() => onChange({ ...filters, showAdvanced: !filters.showAdvanced })}>
          {t('advancedFilters')} {activeCount > 0 ? `(${activeCount})` : ''}
        </Button>
        <Button type="button" onClick={onApply}>{t('applyFilters')}</Button>
        <Button type="button" variant="secondary" onClick={onClear}>{t('clearFilters')}</Button>
      </div>
      {filters.showAdvanced ? (
        <div className="company-filters__grid">
          <label className="company-filters__field">
            <span>{t('countryLabel')}</span>
            <input
              value={filters.country ?? ''}
              onChange={(event) => onChange({ ...filters, country: event.target.value, page: 1 })}
            />
          </label>
          <label className="company-filters__field">
            <span>{t('stateLabel')}</span>
            <input
              value={filters.state ?? ''}
              onChange={(event) => onChange({ ...filters, state: event.target.value, page: 1 })}
            />
          </label>
          <label className="company-filters__field">
            <span>{t('cityLabel')}</span>
            <input
              value={filters.city ?? ''}
              onChange={(event) => onChange({ ...filters, city: event.target.value, page: 1 })}
            />
          </label>
          <label className="company-filters__field">
            <span>{t('typeLabel')}</span>
            <select
              value={filters.branch_type ?? ''}
              onChange={(event) => onChange({ ...filters, branch_type: event.target.value || undefined, page: 1 })}
            >
              <option value="">{t('allTypes')}</option>
              {BRANCH_TYPES.map((value) => (
                <option key={value} value={value}>{tTypes(value)}</option>
              ))}
            </select>
          </label>
          <label className="company-filters__field">
            <span>{t('statusLabel')}</span>
            <select
              value={filters.status ?? ''}
              onChange={(event) => onChange({ ...filters, status: event.target.value || undefined, page: 1 })}
            >
              <option value="">{t('allStatuses')}</option>
              {BRANCH_STATUSES.map((value) => (
                <option key={value} value={value}>{tStatuses(value)}</option>
              ))}
            </select>
          </label>
          <label className="company-filters__field company-filters__field--checkbox">
            <input
              type="checkbox"
              checked={Boolean(filters.include_archived)}
              onChange={(event) => onChange({ ...filters, include_archived: event.target.checked, page: 1 })}
            />
            <span>{t('includeArchived')}</span>
          </label>
        </div>
      ) : null}
    </div>
  );
}
