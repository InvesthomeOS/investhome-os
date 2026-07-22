'use client';

import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

export type CampaignFilterState = {
  search: string;
  status: string;
  campaign_type: string;
  primary_channel?: string;
  project_id?: string;
  owner_user_id?: string;
  objective?: string;
  missing_owner?: boolean;
  missing_budget?: boolean;
  missing_tracking?: boolean;
  my_campaigns?: boolean;
  include_archived?: boolean;
  page: number;
  page_size: number;
};

type CampaignFiltersProps = {
  filters: CampaignFilterState;
  onChange: (filters: CampaignFilterState) => void;
  onApply: () => void;
  onReset: () => void;
};

const PRIMARY_CHANNELS = [
  'meta',
  'google',
  'seo',
  'email',
  'sms',
  'whatsapp',
  'content',
  'youtube',
  'linkedin',
  'referral',
  'event',
  'other',
] as const;

export function CampaignFilters({ filters, onChange, onApply, onReset }: CampaignFiltersProps) {
  const t = useTranslations('marketing.campaigns.filters');
  const tStatus = useTranslations('marketing.campaigns.status');
  const tTypes = useTranslations('marketing.campaigns.types');
  const tChannels = useTranslations('marketing.campaigns.channels');

  return (
    <div className="crm-filters" style={{ marginBottom: '1rem' }}>
      <div className="crm-filters__row">
        <input
          type="search"
          placeholder={t('searchPlaceholder')}
          value={filters.search}
          onChange={(e) => onChange({ ...filters, search: e.target.value })}
          className="crm-filters__search"
        />
        <select
          value={filters.status}
          onChange={(e) => onChange({ ...filters, status: e.target.value })}
          aria-label={t('status')}
        >
          <option value="">{t('allStatuses')}</option>
          {[
            'draft',
            'planning',
            'pending_approval',
            'approved',
            'scheduled',
            'active',
            'paused',
            'completed',
            'cancelled',
          ].map((s) => (
            <option key={s} value={s}>
              {tStatus(s)}
            </option>
          ))}
        </select>
        <select
          value={filters.campaign_type}
          onChange={(e) => onChange({ ...filters, campaign_type: e.target.value })}
          aria-label={t('type')}
        >
          <option value="">{t('allTypes')}</option>
          {[
            'lead_generation',
            'property_launch',
            'project_launch',
            'brand_awareness',
            'retargeting',
            'other',
          ].map((type) => (
            <option key={type} value={type}>
              {tTypes(type)}
            </option>
          ))}
        </select>
        <select
          value={filters.primary_channel ?? ''}
          onChange={(e) => onChange({ ...filters, primary_channel: e.target.value })}
          aria-label={t('channel')}
        >
          <option value="">{t('allChannels')}</option>
          {PRIMARY_CHANNELS.map((channel) => (
            <option key={channel} value={channel}>
              {tChannels(channel)}
            </option>
          ))}
        </select>
        <input
          type="text"
          placeholder={t('projectId')}
          value={filters.project_id ?? ''}
          onChange={(e) => onChange({ ...filters, project_id: e.target.value })}
          aria-label={t('projectId')}
        />
        <input
          type="text"
          placeholder={t('ownerId')}
          value={filters.owner_user_id ?? ''}
          onChange={(e) => onChange({ ...filters, owner_user_id: e.target.value })}
          aria-label={t('ownerId')}
        />
        <label className="crm-filters__checkbox">
          <input
            type="checkbox"
            checked={filters.missing_budget ?? false}
            onChange={(e) => onChange({ ...filters, missing_budget: e.target.checked })}
          />
          {t('missingBudget')}
        </label>
        <label className="crm-filters__checkbox">
          <input
            type="checkbox"
            checked={filters.missing_tracking ?? false}
            onChange={(e) => onChange({ ...filters, missing_tracking: e.target.checked })}
          />
          {t('missingTracking')}
        </label>
        <label className="crm-filters__checkbox">
          <input
            type="checkbox"
            checked={filters.include_archived ?? false}
            onChange={(e) => onChange({ ...filters, include_archived: e.target.checked })}
          />
          {t('includeArchived')}
        </label>
        <Button onClick={onApply}>{t('apply')}</Button>
        <Button variant="ghost" onClick={onReset}>
          {t('reset')}
        </Button>
      </div>
    </div>
  );
}
