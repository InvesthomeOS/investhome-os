'use client';

import { useTranslations } from 'next-intl';

import { Button, FilterBar, Input } from '@investhome/ui';

export type RelationshipFilterState = {
  search: string;
  status?: string;
  category?: string;
  relationship_type?: string;
  page: number;
  page_size: number;
  sort_by: string;
  sort_dir: 'asc' | 'desc';
};

type Props = {
  filters: RelationshipFilterState;
  onChange: (filters: RelationshipFilterState) => void;
  onApply: () => void;
  onClear: () => void;
};

export function RelationshipFilters({ filters, onChange, onApply, onClear }: Props) {
  const t = useTranslations('crm.relationships.filters');
  const tCommon = useTranslations('common');

  return (
    <FilterBar
      actions={
        <>
          <Button type="button" variant="secondary" onClick={onApply}>
            {tCommon('apply')}
          </Button>
          <Button type="button" variant="secondary" onClick={onClear}>
            {tCommon('reset')}
          </Button>
        </>
      }
    >
      <Input
        value={filters.search}
        onChange={(event) => onChange({ ...filters, search: event.target.value })}
        placeholder={t('searchPlaceholder')}
        aria-label={t('searchPlaceholder')}
      />
      <select
        value={filters.status ?? ''}
        onChange={(e) => onChange({ ...filters, status: e.target.value || undefined })}
        aria-label={t('status')}
      >
        <option value="">{t('allStatuses')}</option>
        <option value="active">{t('active')}</option>
        <option value="inactive">{t('inactive')}</option>
        <option value="pending">{t('pending')}</option>
        <option value="archived">{t('archived')}</option>
      </select>
      <select
        value={filters.category ?? ''}
        onChange={(e) => onChange({ ...filters, category: e.target.value || undefined })}
        aria-label={t('category')}
      >
        <option value="">{t('allCategories')}</option>
        <option value="organizational">{t('organizational')}</option>
        <option value="commercial">{t('commercial')}</option>
        <option value="personal">{t('personal')}</option>
        <option value="referral">{t('referral')}</option>
        <option value="investment">{t('investment')}</option>
        <option value="operational">{t('operational')}</option>
      </select>
      <select
        value={filters.relationship_type ?? ''}
        onChange={(e) => onChange({ ...filters, relationship_type: e.target.value || undefined })}
        aria-label={t('type')}
      >
        <option value="">{t('allTypes')}</option>
        <option value="parent">{t('parent')}</option>
        <option value="subsidiary">{t('subsidiary')}</option>
        <option value="partner">{t('partner')}</option>
        <option value="client">{t('client')}</option>
        <option value="vendor">{t('vendor')}</option>
        <option value="referred_by">{t('referredBy')}</option>
        <option value="colleague">{t('colleague')}</option>
      </select>
    </FilterBar>
  );
}
