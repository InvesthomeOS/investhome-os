'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';

import { OPPORTUNITY_STAGES, type OpportunityStage } from '@/lib/api/sales';
import { type LeadStatus } from '@/lib/api/leads';
import { useLeadLabels } from '@/lib/i18n/lead-labels';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

export interface SalesFilterState {
  search: string;
  stage: OpportunityStage | '';
  lead_status: LeadStatus | '';
  assigned_sales_user_id: string;
  party_id: string;
  lead_id: string;
  priority: string;
  include_archived: boolean;
  sort_by: string;
  sort_dir: 'asc' | 'desc';
  page: number;
  page_size: number;
  view: 'pipeline' | 'list' | 'leads';
}

interface SalesFiltersProps {
  filters: SalesFilterState;
  users: { id: string; full_name: string }[];
  onChange: (next: SalesFilterState) => void;
  onApply: () => void;
  onReset: () => void;
}

export function SalesFilters({
  filters,
  users,
  onChange,
  onApply,
  onReset,
}: SalesFiltersProps) {
  const t = useTranslations('sales');
  const tLeads = useTranslations('leads');
  const tCommon = useTranslations('common');
  const { getStageLabel, getPriorityLabel } = useSalesLabels();
  const { statusOptions } = useLeadLabels();
  const leadsView = filters.view === 'leads';

  const activeChips = useMemo(() => {
    const chips: { key: keyof SalesFilterState; label: string }[] = [];
    if (filters.search.trim()) {
      chips.push({ key: 'search', label: `${t('filters.search')}: ${filters.search}` });
    }
    if (filters.stage && !leadsView) {
      chips.push({ key: 'stage', label: getStageLabel(filters.stage) });
    }
    if (filters.lead_status) {
      const status = statusOptions.find((item) => item.value === filters.lead_status);
      chips.push({ key: 'lead_status', label: status?.label ?? filters.lead_status });
    }
    if (filters.assigned_sales_user_id && !leadsView) {
      const user = users.find((u) => u.id === filters.assigned_sales_user_id);
      chips.push({
        key: 'assigned_sales_user_id',
        label: user?.full_name ?? filters.assigned_sales_user_id,
      });
    }
    if (filters.priority && !leadsView) {
      chips.push({ key: 'priority', label: getPriorityLabel(filters.priority) });
    }
    if (filters.include_archived && !leadsView) {
      chips.push({ key: 'include_archived', label: t('filters.includeArchived') });
    }
    return chips;
  }, [filters, getPriorityLabel, getStageLabel, leadsView, statusOptions, t, users]);

  const clearChip = (key: keyof SalesFilterState) => {
    const cleared: Partial<SalesFilterState> = {
      search: '',
      stage: '',
      lead_status: '',
      assigned_sales_user_id: '',
      party_id: '',
      lead_id: '',
      priority: '',
      include_archived: false,
    };
    onChange({ ...filters, ...{ [key]: cleared[key] ?? '' }, page: 1 });
  };

  return (
    <div className="sales__filters-wrap">
      <div className="leads__filters">
        <label className="leads__field">
          <span>{t('filters.search')}</span>
          <input
            type="search"
            value={filters.search}
            onChange={(e) => onChange({ ...filters, search: e.target.value, page: 1 })}
            placeholder={leadsView ? tLeads('searchPlaceholder') : t('filters.searchPlaceholder')}
          />
        </label>
        {leadsView ? (
          <label className="leads__field">
            <span>{tLeads('statusLabel')}</span>
            <select
              value={filters.lead_status}
              onChange={(e) =>
                onChange({ ...filters, lead_status: e.target.value as LeadStatus | '', page: 1 })
              }
            >
              <option value="">{tLeads('allStatuses')}</option>
              {statusOptions.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <>
            <label className="leads__field">
              <span>{t('filters.stage')}</span>
              <select
                value={filters.stage}
                onChange={(e) =>
                  onChange({ ...filters, stage: e.target.value as OpportunityStage | '', page: 1 })
                }
              >
                <option value="">{t('filters.allStages')}</option>
                {OPPORTUNITY_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {getStageLabel(stage)}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field">
              <span>{t('filters.assignee')}</span>
              <select
                value={filters.assigned_sales_user_id}
                onChange={(e) =>
                  onChange({ ...filters, assigned_sales_user_id: e.target.value, page: 1 })
                }
              >
                <option value="">{t('filters.allAssignees')}</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field">
              <span>{t('filters.priority')}</span>
              <select
                value={filters.priority}
                onChange={(e) => onChange({ ...filters, priority: e.target.value, page: 1 })}
              >
                <option value="">{t('filters.allPriorities')}</option>
                {['low', 'medium', 'high', 'urgent'].map((priority) => (
                  <option key={priority} value={priority}>
                    {getPriorityLabel(priority)}
                  </option>
                ))}
              </select>
            </label>
            <label className="leads__field leads__field--checkbox">
              <input
                type="checkbox"
                checked={filters.include_archived}
                onChange={(e) => onChange({ ...filters, include_archived: e.target.checked, page: 1 })}
              />
              <span>{t('filters.includeArchived')}</span>
            </label>
          </>
        )}
      </div>
      <div className="leads__filter-actions">
        <button type="button" className="leads__button leads__button--primary" onClick={onApply}>
          {tCommon('apply')}
        </button>
        <button type="button" className="leads__button leads__button--secondary" onClick={onReset}>
          {tCommon('reset')}
        </button>
      </div>
      {activeChips.length > 0 && (
        <div className="sales__filter-chips">
          {activeChips.map((chip) => (
            <button
              key={chip.key}
              type="button"
              className="sales__filter-chip"
              onClick={() => clearChip(chip.key)}
            >
              {chip.label} ×
            </button>
          ))}
          <button type="button" className="sales__filter-chip" onClick={onReset}>
            {t('filters.clearAll')}
          </button>
        </div>
      )}
    </div>
  );
}
