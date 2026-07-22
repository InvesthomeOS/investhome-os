'use client';

import { useTranslations } from 'next-intl';

import { useBiFilters } from '@/lib/analytics/bi-filters';
import type { BiFilterPreset } from '@/lib/analytics/bi-types';

const PRESETS: BiFilterPreset[] = ['today', '7d', '30d', 'quarter', 'ytd', 'custom'];

export function BiFilterBar() {
  const t = useTranslations('analytics.filters');
  const { filters, setFilters, setPreset } = useBiFilters();

  return (
    <section className="bi-filters" aria-label={t('aria')}>
      <div className="bi-filters__presets" role="group" aria-label={t('presets')}>
        {PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            className={`bi-filters__chip${filters.preset === preset ? ' bi-filters__chip--active' : ''}`}
            onClick={() => setPreset(preset)}
            aria-pressed={filters.preset === preset}
          >
            {t(`preset.${preset}`)}
          </button>
        ))}
      </div>

      <div className="bi-filters__grid">
        <label className="bi-filters__field">
          <span>{t('dateFrom')}</span>
          <input
            type="date"
            value={filters.date_from ?? ''}
            onChange={(e) =>
              setFilters({
                date_from: e.target.value || undefined,
                preset: 'custom',
              })
            }
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('dateTo')}</span>
          <input
            type="date"
            value={filters.date_to ?? ''}
            onChange={(e) =>
              setFilters({
                date_to: e.target.value || undefined,
                preset: 'custom',
              })
            }
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('comparison')}</span>
          <select
            value={filters.comparison ?? 'previous_period'}
            onChange={(e) =>
              setFilters({ comparison: e.target.value as 'previous_period' | 'none' })
            }
          >
            <option value="previous_period">{t('comparisonPrevious')}</option>
            <option value="none">{t('comparisonNone')}</option>
          </select>
        </label>
        <label className="bi-filters__field">
          <span>{t('currency')}</span>
          <input
            type="text"
            maxLength={3}
            placeholder="TRY"
            value={filters.currency ?? ''}
            onChange={(e) => setFilters({ currency: e.target.value.toUpperCase() || undefined })}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('project')}</span>
          <input
            type="text"
            value={filters.project_id ?? ''}
            onChange={(e) => setFilters({ project_id: e.target.value || undefined })}
            placeholder={t('projectPlaceholder')}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('teamMember')}</span>
          <input
            type="text"
            value={filters.assigned_to ?? ''}
            onChange={(e) => setFilters({ assigned_to: e.target.value || undefined })}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('leadSource')}</span>
          <input
            type="text"
            value={filters.lead_source ?? ''}
            onChange={(e) => setFilters({ lead_source: e.target.value || undefined })}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('campaign')}</span>
          <input
            type="text"
            value={filters.campaign_id ?? ''}
            onChange={(e) => setFilters({ campaign_id: e.target.value || undefined })}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('investor')}</span>
          <input
            type="text"
            value={filters.investor_id ?? ''}
            onChange={(e) => setFilters({ investor_id: e.target.value || undefined })}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('status')}</span>
          <input
            type="text"
            value={filters.status ?? ''}
            onChange={(e) => setFilters({ status: e.target.value || undefined })}
          />
        </label>
        <label className="bi-filters__field">
          <span>{t('workspace')}</span>
          <input
            type="text"
            value={filters.workspace ?? ''}
            onChange={(e) => setFilters({ workspace: e.target.value || undefined })}
          />
        </label>
      </div>
    </section>
  );
}
