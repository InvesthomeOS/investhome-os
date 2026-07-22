'use client';

import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import type { ActivityListParams } from '@/workspaces/crm/types/activities';
import {
  CRM_ACTIVITY_PRIORITIES,
  CRM_ACTIVITY_STATUSES,
  CRM_ACTIVITY_TYPES,
} from '@/workspaces/crm/types/activities';

export type ActivityFilterState = ActivityListParams;

type ActivityFiltersProps = {
  filters: ActivityFilterState;
  filterLogic: 'and' | 'or';
  onChange: (filters: ActivityFilterState) => void;
  onFilterLogicChange: (logic: 'and' | 'or') => void;
  onApply: () => void;
  onReset: () => void;
  showEntityFilters?: boolean;
};

export function ActivityFilters({
  filters,
  filterLogic,
  onChange,
  onFilterLogicChange,
  onApply,
  onReset,
  showEntityFilters = true,
}: ActivityFiltersProps) {
  const t = useTranslations('crm.activities.filters');

  return (
    <section className="crm-activity-filters" aria-label={t('ariaLabel')}>
      <div className="crm-activity-filters__row">
        <input
          type="search"
          className="crm-activity-filters__search"
          placeholder={t('searchPlaceholder')}
          value={filters.search ?? ''}
          onChange={(event) => onChange({ ...filters, search: event.target.value, page: 1 })}
        />
        <select
          className="crm-activity-filters__select"
          value={filters.activity_type ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              activity_type: event.target.value ? (event.target.value as ActivityFilterState['activity_type']) : undefined,
              page: 1,
            })
          }
        >
          <option value="">{t('allTypes')}</option>
          {CRM_ACTIVITY_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <select
          className="crm-activity-filters__select"
          value={filters.status ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              status: event.target.value ? (event.target.value as ActivityFilterState['status']) : undefined,
              page: 1,
            })
          }
        >
          <option value="">{t('allStatuses')}</option>
          {CRM_ACTIVITY_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
        <select
          className="crm-activity-filters__select"
          value={filters.priority ?? ''}
          onChange={(event) =>
            onChange({
              ...filters,
              priority: event.target.value ? (event.target.value as ActivityFilterState['priority']) : undefined,
              page: 1,
            })
          }
        >
          <option value="">{t('allPriorities')}</option>
          {CRM_ACTIVITY_PRIORITIES.map((priority) => (
            <option key={priority} value={priority}>
              {priority}
            </option>
          ))}
        </select>
      </div>
      <div className="crm-activity-filters__row">
        {showEntityFilters && (
          <>
            <select
              className="crm-activity-filters__select"
              value={filters.entity_type ?? ''}
              onChange={(event) =>
                onChange({
                  ...filters,
                  entity_type: event.target.value
                    ? (event.target.value as ActivityFilterState['entity_type'])
                    : undefined,
                  page: 1,
                })
              }
            >
              <option value="">{t('allEntities')}</option>
              <option value="contact">{t('entityContact')}</option>
              <option value="company">{t('entityCompany')}</option>
              <option value="relationship">{t('entityRelationship')}</option>
            </select>
            <input
              type="date"
              className="crm-activity-filters__date"
              value={filters.date_from?.slice(0, 10) ?? ''}
              onChange={(event) =>
                onChange({
                  ...filters,
                  date_from: event.target.value ? `${event.target.value}T00:00:00.000Z` : undefined,
                  page: 1,
                })
              }
            />
            <input
              type="date"
              className="crm-activity-filters__date"
              value={filters.date_to?.slice(0, 10) ?? ''}
              onChange={(event) =>
                onChange({
                  ...filters,
                  date_to: event.target.value ? `${event.target.value}T23:59:59.999Z` : undefined,
                  page: 1,
                })
              }
            />
          </>
        )}
        <div className="crm-activity-filters__logic" role="group" aria-label={t('filterLogic')}>
          <button
            type="button"
            className={filterLogic === 'and' ? 'crm-activity-filters__logic-btn--active' : 'crm-activity-filters__logic-btn'}
            onClick={() => onFilterLogicChange('and')}
          >
            {t('and')}
          </button>
          <button
            type="button"
            className={filterLogic === 'or' ? 'crm-activity-filters__logic-btn--active' : 'crm-activity-filters__logic-btn'}
            onClick={() => onFilterLogicChange('or')}
          >
            {t('or')}
          </button>
        </div>
        <label className="crm-activity-filters__checkbox">
          <input
            type="checkbox"
            checked={Boolean(filters.pending)}
            onChange={(event) => onChange({ ...filters, pending: event.target.checked || undefined, page: 1 })}
          />
          {t('pendingOnly')}
        </label>
        <label className="crm-activity-filters__checkbox">
          <input
            type="checkbox"
            checked={Boolean(filters.completed)}
            onChange={(event) => onChange({ ...filters, completed: event.target.checked || undefined, page: 1 })}
          />
          {t('completedOnly')}
        </label>
      </div>
      <div className="crm-activity-filters__actions">
        <Button type="button" onClick={onApply}>
          {t('apply')}
        </Button>
        <Button type="button" variant="secondary" onClick={onReset}>
          {t('reset')}
        </Button>
      </div>
    </section>
  );
}
