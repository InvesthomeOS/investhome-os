'use client';

import { useMemo, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import {
  exportPerformanceReport,
  fetchChannelPerformance,
  fetchCampaignPerformanceList,
  fetchPerformanceOverview,
  fetchProjectPerformance,
  type PerformanceMetric,
  type PerformanceQueryParams,
} from '@/workspaces/marketing/api/performance';

import { MetricRow, TableWidget } from '../dashboard/_components/analytics-widgets';

function metricState(metric?: PerformanceMetric | null): 'ready' | 'unavailable' | 'empty' | 'unknown' {
  if (!metric) return 'unavailable';
  if (metric.state === 'ready') return 'ready';
  if (metric.state === 'empty') return 'empty';
  return 'unavailable';
}

function formatMetric(metric?: PerformanceMetric | null): string {
  if (!metric || metric.state !== 'ready' || metric.value === null || metric.value === undefined) {
    return '—';
  }
  return String(metric.value);
}

export default function MarketingReportsPage() {
  const t = useTranslations('marketing.reports');
  const tAi = useTranslations('marketing.ai.assistant');
  const tCommon = useTranslations('marketing.common');
  const { user } = useAuth();
  const canView = hasMarketingPermission(user, 'view') || hasMarketingPermission(user, 'export_analytics');
  const canExport = hasMarketingPermission(user, 'export') || hasMarketingPermission(user, 'export_analytics');
  const canAi = hasMarketingPermission(user, 'view_ai');

  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [status, setStatus] = useState('');
  const [exporting, setExporting] = useState<string | null>(null);

  const filters = useMemo<PerformanceQueryParams>(
    () => ({
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      status: status || undefined,
    }),
    [dateFrom, dateTo, status],
  );

  const overviewQuery = useQuery({
    queryKey: ['marketing', 'performance', 'overview', filters],
    queryFn: () => fetchPerformanceOverview(filters),
    enabled: canView,
  });

  const campaignsQuery = useQuery({
    queryKey: ['marketing', 'performance', 'campaigns', filters],
    queryFn: () => fetchCampaignPerformanceList({ ...filters, page: 1, page_size: 50 }),
    enabled: canView,
  });

  const channelsQuery = useQuery({
    queryKey: ['marketing', 'performance', 'channels', filters],
    queryFn: () => fetchChannelPerformance(filters),
    enabled: canView,
  });

  const projectsQuery = useQuery({
    queryKey: ['marketing', 'performance', 'projects', filters],
    queryFn: () => fetchProjectPerformance(filters),
    enabled: canView,
  });

  const handleExport = async (reportType: string) => {
    if (!canExport) return;
    setExporting(reportType);
    try {
      const blob = await exportPerformanceReport(reportType, filters);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `marketing_${reportType}_performance.csv`;
      anchor.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(null);
    }
  };

  if (!canView) {
    return (
      <main className="dashboard marketing-module-shell">
        <header className="dashboard__header">
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </header>
        <EmptyState title={tCommon('permissionRestricted')} description={tCommon('permissionRestrictedDescription')} />
      </main>
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header dashboard__header--row">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('description')}</p>
        </div>
        <div className="marketing-detail__actions">
          {canAi ? (
            <Link href={'/workspaces/marketing/ai/assistant?mode=marketing_summary' as Route} className="button button--secondary">
              {tAi('contextualEntry')}
            </Link>
          ) : null}
          <Link href={'/workspaces/marketing/dashboard/executive' as Route} className="button">
            {t('openDashboard')}
          </Link>
        </div>
      </header>

      <section className="marketing-dashboard__section">
        <div className="crm-filters" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <label>
            {t('filters.dateFrom')}
            <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
          </label>
          <label>
            {t('filters.dateTo')}
            <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
          </label>
          <label>
            {t('filters.status')}
            <input
              type="text"
              value={status}
              onChange={(event) => setStatus(event.target.value)}
              placeholder="active"
            />
          </label>
        </div>
        {canExport ? (
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.75rem' }}>
            {(['campaigns', 'channel', 'project', 'lead_attribution'] as const).map((type) => (
              <Button key={type} type="button" onClick={() => void handleExport(type)} disabled={exporting === type}>
                {exporting === type ? tCommon('loading') : t(`export.${type}` as 'export.campaigns')}
              </Button>
            ))}
          </div>
        ) : null}
      </section>

      {overviewQuery.isLoading ? (
        <LoadingState label={tCommon('loading')} />
      ) : overviewQuery.isError ? (
        <ErrorState
          title={tCommon('error')}
          message={overviewQuery.error instanceof ApiError ? overviewQuery.error.message : tCommon('error')}
          action={
            <Button type="button" onClick={() => void overviewQuery.refetch()}>
              {t('retry')}
            </Button>
          }
        />
      ) : (
        <section className="marketing-dashboard__section">
          <h2 className="marketing-dashboard__section-title">{t('kpiSection')}</h2>
          <MetricRow
            metrics={[
              {
                label: t('metrics.totalCampaigns'),
                value: overviewQuery.data?.total_campaigns.value ?? null,
                state: metricState(overviewQuery.data?.total_campaigns),
              },
              {
                label: t('metrics.totalLeads'),
                value: overviewQuery.data?.total_leads.value ?? null,
                state: metricState(overviewQuery.data?.total_leads),
              },
              {
                label: t('metrics.qualifiedLeads'),
                value: overviewQuery.data?.qualified_leads.value ?? null,
                state: metricState(overviewQuery.data?.qualified_leads),
              },
              {
                label: t('metrics.convertedLeads'),
                value: overviewQuery.data?.converted_leads.value ?? null,
                state: metricState(overviewQuery.data?.converted_leads),
              },
              {
                label: t('metrics.avgCpl'),
                value: overviewQuery.data?.avg_cpl.value ?? null,
                state: metricState(overviewQuery.data?.avg_cpl),
              },
              {
                label: t('metrics.avgConversionRate'),
                value: overviewQuery.data?.avg_conversion_rate.value ?? null,
                state: metricState(overviewQuery.data?.avg_conversion_rate),
              },
            ]}
          />
        </section>
      )}

      <section className="marketing-dashboard__section">
        <h2 className="marketing-dashboard__section-title">{t('campaignPerformance')}</h2>
        {campaignsQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : (campaignsQuery.data?.items.length ?? 0) === 0 ? (
          <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
        ) : (
          <TableWidget
            columns={['campaign', 'leads', 'qualified', 'conversions', 'cpl', 'conversionRate']}
            columnLabels={{
              campaign: t('columns.campaign'),
              leads: t('columns.leads'),
              qualified: t('columns.qualified'),
              conversions: t('columns.conversions'),
              cpl: t('columns.cpl'),
              conversionRate: t('columns.conversionRate'),
            }}
            rows={(campaignsQuery.data?.items ?? []).map((item) => ({
              campaign: item.campaign_name,
              leads: formatMetric(item.total_leads),
              qualified: formatMetric(item.qualified_leads),
              conversions: formatMetric(item.converted_leads),
              cpl: formatMetric(item.cpl),
              conversionRate: formatMetric(item.conversion_rate),
            }))}
          />
        )}
      </section>

      <section className="marketing-dashboard__section">
        <h2 className="marketing-dashboard__section-title">{t('channelPerformance')}</h2>
        {(channelsQuery.data?.items.length ?? 0) === 0 ? (
          <EmptyState title={t('emptyChannels')} />
        ) : (
          <TableWidget
            columns={['channel', 'leads', 'qualified', 'conversions', 'cpl', 'conversionRate']}
            columnLabels={{
              channel: t('columns.channel'),
              leads: t('columns.leads'),
              qualified: t('columns.qualified'),
              conversions: t('columns.conversions'),
              cpl: t('columns.cpl'),
              conversionRate: t('columns.conversionRate'),
            }}
            rows={(channelsQuery.data?.items ?? []).map((item) => ({
              channel: item.channel,
              leads: formatMetric(item.leads),
              qualified: formatMetric(item.qualified_leads),
              conversions: formatMetric(item.conversions),
              cpl: formatMetric(item.cpl),
              conversionRate: formatMetric(item.conversion_rate),
            }))}
          />
        )}
      </section>

      <section className="marketing-dashboard__section">
        <h2 className="marketing-dashboard__section-title">{t('projectPerformance')}</h2>
        {(projectsQuery.data?.items.length ?? 0) === 0 ? (
          <EmptyState title={t('emptyProjects')} />
        ) : (
          <TableWidget
            columns={['project', 'leads', 'qualified', 'conversions', 'cpl', 'conversionRate']}
            columnLabels={{
              project: t('columns.project'),
              leads: t('columns.leads'),
              qualified: t('columns.qualified'),
              conversions: t('columns.conversions'),
              cpl: t('columns.cpl'),
              conversionRate: t('columns.conversionRate'),
            }}
            rows={(projectsQuery.data?.items ?? []).map((item) => ({
              project: item.project_name,
              leads: formatMetric(item.leads),
              qualified: formatMetric(item.qualified_leads),
              conversions: formatMetric(item.conversions),
              cpl: formatMetric(item.cpl),
              conversionRate: formatMetric(item.conversion_rate),
            }))}
          />
        )}
      </section>
    </main>
  );
}
