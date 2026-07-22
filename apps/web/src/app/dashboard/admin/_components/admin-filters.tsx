'use client';

import { Button, FilterBar, SearchInput, Select } from '@investhome/ui';
import { useTranslations } from 'next-intl';

export type AdminFilterState = {
  search: string;
  status: string;
  roleId: string;
  department: string;
  dateFrom: string;
  dateTo: string;
};

export const DEFAULT_ADMIN_FILTERS: AdminFilterState = {
  search: '',
  status: '',
  roleId: '',
  department: '',
  dateFrom: '',
  dateTo: '',
};

type AdminFiltersProps = {
  filters: AdminFilterState;
  onChange: (next: AdminFilterState) => void;
  onApply: () => void;
  onReset: () => void;
  roleOptions?: { value: string; label: string }[];
  showRole?: boolean;
  showDepartment?: boolean;
  showDate?: boolean;
};

export function AdminFilters({
  filters,
  onChange,
  onApply,
  onReset,
  roleOptions = [],
  showRole = false,
  showDepartment = false,
  showDate = false,
}: AdminFiltersProps) {
  const t = useTranslations('adminShell.filters');
  const tCommon = useTranslations('common');

  const statusOptions = [
    { value: '', label: t('allStatuses') },
    { value: 'active', label: t('statusActive') },
    { value: 'inactive', label: t('statusInactive') },
    { value: 'suspended', label: t('statusSuspended') },
    { value: 'invited', label: t('statusInvited') },
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
        {statusOptions.map((option) => (
          <option key={option.value || '__all'} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
      {showRole ? (
        <Select
          label={t('role')}
          value={filters.roleId}
          onChange={(event) => onChange({ ...filters, roleId: event.target.value })}
        >
          <option value="">{t('allRoles')}</option>
          {roleOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      ) : null}
      {showDepartment ? (
        <SearchInput
          value={filters.department}
          onChange={(event) => onChange({ ...filters, department: event.target.value })}
          placeholder={t('departmentPlaceholder')}
          aria-label={t('departmentPlaceholder')}
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
