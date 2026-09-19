'use client';

import { useLocale, useTranslations } from 'next-intl';

import { AreaChart, LineChart } from '@/components/design-system/charts';

import { CrmKpiSpark } from './crm-kpi-spark';

export type CrmAnalyticsStripProps = {
  /** Primary KPI spark series */
  contactTrend?: number[];
  activityTrend?: number[];
  pipelineTrend?: number[];
  revenueTrend?: { label: string; value: number }[];
  engagementTrend?: { label: string; value: number }[];
  contactCount?: number;
  activityCount?: number;
  pipelineValue?: string;
  className?: string;
  /** When true, only KPI sparklines (no full charts) — denser CRM lists/boards. */
  compact?: boolean;
};

/**
 * Compact Attio/Stripe-inspired analytics strip for CRM surfaces.
 * Line charts primary; area only for trend comparison; sparklines in KPIs.
 */
export function CrmAnalyticsStrip({
  contactTrend = [12, 14, 13, 18, 20, 19, 24],
  activityTrend = [4, 6, 5, 8, 7, 9, 11],
  pipelineTrend = [2.1, 2.4, 2.2, 2.8, 3.1, 2.9, 3.4],
  revenueTrend,
  engagementTrend,
  contactCount = 0,
  activityCount = 0,
  pipelineValue = '—',
  className,
  compact = false,
}: CrmAnalyticsStripProps) {
  const t = useTranslations('crm.g2.analytics');
  const locale = useLocale();

  const defaultRevenue =
    revenueTrend ??
    [
      { label: 'P1', value: 1.2 },
      { label: 'P2', value: 1.5 },
      { label: 'P3', value: 1.4 },
      { label: 'P4', value: 1.9 },
      { label: 'P5', value: 2.2 },
      { label: 'P6', value: 2.0 },
      { label: 'P7', value: 2.6 },
    ].map((p, i) => ({ ...p, label: `W${i + 1}` }));

  const defaultEngagement =
    engagementTrend ??
    defaultRevenue.map((p, i) => ({
      label: p.label,
      value: Math.max(1, Math.round(p.value * 4 + (i % 3))),
    }));

  return (
    <section
      className={`crm-g2-analytics${compact ? ' crm-g2-analytics--compact' : ''}${className ? ` ${className}` : ''}`}
      aria-label={t('section')}
      data-testid="crm-g2-analytics"
    >
      <div className="crm-g2-analytics__kpis">
        <CrmKpiSpark
          label={t('contacts')}
          value={contactCount}
          sparkValues={contactTrend}
          ariaLabel={t('contactsSpark')}
          delta={t('trendUp')}
          deltaTone="up"
        />
        <CrmKpiSpark
          label={t('activities')}
          value={activityCount}
          sparkValues={activityTrend}
          ariaLabel={t('activitiesSpark')}
          delta={t('trendUp')}
          deltaTone="up"
        />
        <CrmKpiSpark
          label={t('pipeline')}
          value={pipelineValue}
          sparkValues={pipelineTrend}
          ariaLabel={t('pipelineSpark')}
          hint={t('pipelineHint')}
        />
      </div>

      {!compact ? (
        <div className="crm-g2-analytics__charts">
          <div className="crm-g2-analytics__chart">
            <LineChart
              data={defaultRevenue}
              ariaLabel={t('revenueLine')}
              title={t('revenueTitle')}
              locale={locale}
              format="currency"
              height={88}
              className="crm-g2-analytics__line"
            />
          </div>
          <div className="crm-g2-analytics__chart">
            <AreaChart
              data={defaultEngagement}
              ariaLabel={t('engagementArea')}
              title={t('engagementTitle')}
              locale={locale}
              format="number"
              height={88}
              className="crm-g2-analytics__area"
            />
          </div>
        </div>
      ) : null}
    </section>
  );
}
