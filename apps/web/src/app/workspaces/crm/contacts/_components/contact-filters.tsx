'use client';

import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import {
  CRM_CONTACT_TYPES,
  CRM_LIFECYCLE_STAGES,
  CRM_PRIORITIES,
  DEFAULT_SAVED_VIEWS,
  type CrmContactPriority,
  type CrmContactStatus,
  type CrmContactType,
  type CrmLifecycleStage,
} from '@/workspaces/crm/types';

export type ContactFilterState = {
  search: string;
  contact_type?: CrmContactType;
  lifecycle_stage?: CrmLifecycleStage;
  priority?: CrmContactPriority;
  status?: CrmContactStatus;
  page: number;
  page_size: number;
  sort_by: string;
  sort_dir: 'asc' | 'desc';
};

type ContactFiltersProps = {
  filters: ContactFilterState;
  onChange: (filters: ContactFilterState) => void;
  onApply: () => void;
  onClear: () => void;
  onPreset: (preset: Partial<ContactFilterState>) => void;
};

export function ContactFilters({ filters, onChange, onApply, onClear, onPreset }: ContactFiltersProps) {
  const t = useTranslations('crm.contacts');
  const tTypes = useTranslations('crm.contactTypes');
  const tLifecycle = useTranslations('crm.contacts.lifecycle');
  const tPriority = useTranslations('crm.contacts.priority');

  return (
    <div className="company-filters crm-contacts__filters">
      <div className="company-filters__row">
        <label className="company-filters__field company-filters__field--grow">
          <span>{t('searchPlaceholder')}</span>
          <input
            type="search"
            value={filters.search}
            placeholder={t('searchPlaceholder')}
            onChange={(event) => onChange({ ...filters, search: event.target.value, page: 1 })}
          />
        </label>
        <Button type="button" onClick={onApply}>
          {t('filters.allTypes')}
        </Button>
        <Button type="button" variant="secondary" onClick={onClear}>
          {t('bulkClear')}
        </Button>
      </div>
      <div className="crm-contacts__filter-row">
        <select
          value={filters.contact_type ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              contact_type: (event.target.value || undefined) as CrmContactType | undefined,
            })
          }
        >
          <option value="">{t('filters.allTypes')}</option>
          {CRM_CONTACT_TYPES.map((type) => (
            <option key={type} value={type}>
              {tTypes(type)}
            </option>
          ))}
        </select>
        <select
          value={filters.lifecycle_stage ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              lifecycle_stage: (event.target.value || undefined) as CrmLifecycleStage | undefined,
            })
          }
        >
          <option value="">{t('filters.allLifecycle')}</option>
          {CRM_LIFECYCLE_STAGES.map((stage) => (
            <option key={stage} value={stage}>
              {tLifecycle(stage)}
            </option>
          ))}
        </select>
        <select
          value={filters.priority ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              priority: (event.target.value || undefined) as CrmContactPriority | undefined,
            })
          }
        >
          <option value="">{t('filters.allPriority')}</option>
          {CRM_PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {tPriority(priority)}
            </option>
          ))}
        </select>
      </div>
      <div className="crm-contacts__presets">
        {DEFAULT_SAVED_VIEWS.map((view) => (
          <Button
            key={view.key}
            type="button"
            variant="ghost"
            onClick={() => onPreset(view.filters as Partial<ContactFilterState>)}
          >
            {t(`presets.${view.key}` as 'presets.all')}
          </Button>
        ))}
      </div>
    </div>
  );
}
