'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import {
  fetchCampaignLeadBreakdown,
  fetchCampaignPerformanceDetail,
  type PerformanceMetric,
} from '@/workspaces/marketing/api/performance';

import { MetricRow, TableWidget } from '../../../dashboard/_components/analytics-widgets';

function metricState(metric?: PerformanceMetric | null): 'ready' | 'unavailable' | 'empty' | 'unknown' {
  if (!metric) return 'unavailable';
  if (metric.state === 'ready') return 'ready';
  if (metric.state === 'empty') return 'empty';
  return 'unavailable';
}

export function CampaignPerformancePanel({
  campaignId,
  mode = 'analytics',
}: {
  campaignId: string;
  mode?: 'analytics' | 'attribution';
}) {
  const t = useTranslations('marketing.campaigns.detail.panels.performance');
  const tCommon = useTranslations('marketing.common');

  const detailQuery = useQuery({
    queryKey: ['marketing', 'performance', 'campaign-detail', campaignId],
    queryFn: () => fetchCampaignPerformanceDetail(campaignId),
  });

  const leadsQuery = useQuery({
    queryKey: ['marketing', 'performance', 'campaign-leads', campaignId, mode],
    queryFn: () => fetchCampaignLeadBreakdown(campaignId),
    enabled: mode === 'attribution',
  });

  if (detailQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (detailQuery.isError) {
    return (
      <ErrorState
        title={tCommon('error')}
        message={detailQuery.error instanceof ApiError ? detailQuery.error.message : tCommon('error')}
      />
    );
  }

  const detail = detailQuery.data as {
    metrics: Record<string, PerformanceMetric | string | null>;
    status_breakdown: Record<string, number>;
    spend_vs_budget: Record<string, string | null>;
    top_sources: Array<{ source: string; count: number }>;
    utm_breakdown: Array<{ utm_source: string; count: number }>;
  } | null;

  if (!detail) {
    return <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />;
  }

  const metrics = detail.metrics;
  const cards = [
    { key: 'planned_budget', label: t('plannedBudget') },
    { key: 'actual_spend', label: t('actualSpend') },
    { key: 'total_leads', label: t('totalLeads') },
    { key: 'qualified_leads', label: t('qualifiedLeads') },
    { key: 'converted_leads', label: t('convertedLeads') },
    { key: 'conversion_rate', label: t('conversionRate') },
    { key: 'cpl', label: t('cpl') },
    { key: 'cpql', label: t('cpql') },
    { key: 'cpc', label: t('cpc') },
    { key: 'estimated_revenue', label: t('estimatedRevenue') },
    { key: 'confirmed_revenue', label: t('confirmedRevenue') },
    { key: 'confirmed_roi', label: t('confirmedRoi') },
  ];

  return (
    <div className="marketing-dashboard__section">
      <h2 className="marketing-dashboard__section-title">{t('title')}</h2>
      <MetricRow
        metrics={cards.map((card) => {
          const metric = metrics[card.key] as PerformanceMetric | undefined;
          return {
            label: card.label,
            value: metric?.value ?? null,
            state: metricState(metric),
          };
        })}
      />

      <div className="marketing-summary__grid" style={{ marginTop: '1.5rem' }}>
        <article className="marketing-summary__card">
          <p className="marketing-summary__label">{t('spendVsBudget')}</p>
          <p className="marketing-summary__value">
            {detail.spend_vs_budget.spent ?? '—'} / {detail.spend_vs_budget.planned ?? '—'}
          </p>
          <p className="marketing-campaign-card__meta">
            {t('remaining')}: {detail.spend_vs_budget.remaining ?? '—'}
          </p>
        </article>
        {Object.entries(detail.status_breakdown).map(([status, count]) => (
          <article key={status} className="marketing-summary__card">
            <p className="marketing-summary__label">{status}</p>
            <p className="marketing-summary__value">{count}</p>
          </article>
        ))}
      </div>

      {mode === 'attribution' ? (
        <>
          <h3 className="marketing-dashboard__section-title" style={{ marginTop: '1.5rem' }}>
            {t('sources')}
          </h3>
          {(detail.top_sources?.length ?? 0) === 0 && (detail.utm_breakdown?.length ?? 0) === 0 ? (
            <EmptyState title={t('emptyAttribution')} description={t('emptyAttributionDescription')} />
          ) : (
            <TableWidget
              columns={['label', 'count']}
              columnLabels={{ label: t('source'), count: t('count') }}
              rows={[
                ...detail.top_sources.map((row) => ({ label: row.source, count: String(row.count) })),
                ...detail.utm_breakdown.map((row) => ({
                  label: `utm:${row.utm_source}`,
                  count: String(row.count),
                })),
              ]}
            />
          )}
          {leadsQuery.isLoading ? (
            <LoadingState label={tCommon('loading')} />
          ) : leadsQuery.data && leadsQuery.data.total > 0 ? (
            <>
              <h3 className="marketing-dashboard__section-title" style={{ marginTop: '1.5rem' }}>
                {t('attributedLeads')}
              </h3>
              <TableWidget
                columns={['full_name', 'attribution_status', 'utm_source', 'attribution_source']}
                columnLabels={{
                  full_name: t('leadName'),
                  attribution_status: t('status'),
                  utm_source: t('utmSource'),
                  attribution_source: t('method'),
                }}
                rows={leadsQuery.data.items.map((item) => ({
                  full_name: item.full_name,
                  attribution_status: item.attribution_status,
                  utm_source: item.utm_source ?? '—',
                  attribution_source: item.attribution_source ?? '—',
                }))}
              />
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
