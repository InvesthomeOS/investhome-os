'use client';

import { Button, FilterBar, SearchInput, Select } from '@investhome/ui';
import { useTranslations } from 'next-intl';

export type CompanyFilterState = {
  search: string;
  status: string;
  country: string;
  companyId: string;
  branchId: string;
  ownerId: string;
  dateFrom: string;
  dateTo: string;
  tags: string;
};

export const DEFAULT_COMPANY_FILTERS: CompanyFilterState = {
  search: '',
  status: '',
  country: '',
  companyId: '',
  branchId: '',
  ownerId: '',
  dateFrom: '',
  dateTo: '',
  tags: '',
};

type CompanyFiltersProps = {
  filters: CompanyFilterState;
  onChange: (next: CompanyFilterState) => void;
  onApply: () => void;
  onReset: () => void;
  showCompany?: boolean;
  showBranch?: boolean;
  showOwner?: boolean;
  showDate?: boolean;
  showTags?: boolean;
  statusOptions?: { value: string; label: string }[];
};

export function CompanyFilters({
  filters,
  onChange,
  onApply,
  onReset,
  showCompany = false,
  showBranch = false,
  showOwner = false,
  showDate = true,
  showTags = false,
  statusOptions,
}: CompanyFiltersProps) {
  const t = useTranslations('company.filters');
  const tCommon = useTranslations('common');

  const statuses = statusOptions ?? [
    { value: '', label: t('allStatuses') },
    { value: 'active', label: t('statusActive') },
    { value: 'inactive', label: t('statusInactive') },
    { value: 'draft', label: t('statusDraft') },
    { value: 'archived', label: t('statusArchived') },
  ];

  return (
    <FilterBar
      actions={
        <>
          <Button type="button" variant="secondary" onClick={onReset}>
            {tCommon('reset')}
          </Button>
          <Button type="button" onClick={onApply}>
            {tCommon('apply')}
          </Button>
        </>
      }
    >
      <SearchInput
        value={filters.search}
        onChange={(event) => onChange({ ...filters, search: event.target.value })}
        placeholder={t('searchPlaceholder')}
        aria-label={t('searchPlaceholder')}
      />
      <Select
        label={t('status')}
        value={filters.status}
        onChange={(event) => onChange({ ...filters, status: event.target.value })}
      >
        {statuses.map((option) => (
          <option key={option.value || '__all'} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
      <SearchInput
        value={filters.country}
        onChange={(event) => onChange({ ...filters, country: event.target.value })}
        placeholder={t('countryPlaceholder')}
        aria-label={t('countryPlaceholder')}
      />
      {showCompany ? (
        <SearchInput
          value={filters.companyId}
          onChange={(event) => onChange({ ...filters, companyId: event.target.value })}
          placeholder={t('companyPlaceholder')}
          aria-label={t('companyPlaceholder')}
        />
      ) : null}
      {showBranch ? (
        <SearchInput
          value={filters.branchId}
          onChange={(event) => onChange({ ...filters, branchId: event.target.value })}
          placeholder={t('branchPlaceholder')}
          aria-label={t('branchPlaceholder')}
        />
      ) : null}
      {showOwner ? (
        <SearchInput
          value={filters.ownerId}
          onChange={(event) => onChange({ ...filters, ownerId: event.target.value })}
          placeholder={t('ownerPlaceholder')}
          aria-label={t('ownerPlaceholder')}
        />
      ) : null}
      {showTags ? (
        <SearchInput
          value={filters.tags}
          onChange={(event) => onChange({ ...filters, tags: event.target.value })}
          placeholder={t('tagsPlaceholder')}
          aria-label={t('tagsPlaceholder')}
        />
      ) : null}
      {showDate ? (
        <>
          <label className="ih-field">
            <span className="ih-field__label">{t('dateFrom')}</span>
            <input
              type="date"
              className="ih-input"
              value={filters.dateFrom}
              onChange={(event) => onChange({ ...filters, dateFrom: event.target.value })}
            />
          </label>
          <label className="ih-field">
            <span className="ih-field__label">{t('dateTo')}</span>
            <input
              type="date"
              className="ih-input"
              value={filters.dateTo}
              onChange={(event) => onChange({ ...filters, dateTo: event.target.value })}
            />
          </label>
        </>
      ) : null}
    </FilterBar>
  );
}
