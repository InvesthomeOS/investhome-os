'use client';

import { resolveMarketingMetricLabel } from '@/lib/marketing/marketing-i18n';
import { marketingQueries } from '@/lib/query/marketing-queries';

import { MetricRow, TableWidget, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function PerformanceDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="performance.title"
      subtitleKey="performance.subtitle"
      queryOptions={marketingQueries.dashboardExecutive()}
      render={(data, t) => (
        <div className="mkt-analytics-grid">
          <WidgetShell title={t('sections.kpiBar')} state="ready">
            <MetricRow
              metrics={data.kpis.map((k) => ({
                label: resolveMarketingMetricLabel(t, k.key, k.label),
                value: typeof k.value === 'number' || typeof k.value === 'string' ? k.value : null,
                unit: k.unit,
                state: k.state,
                evidence: k.evidence,
              }))}
            />
          </WidgetShell>
          <WidgetShell title={t('sections.channels')} state={data.channel_summaries.length ? 'ready' : 'empty'}>
            <TableWidget
              rows={data.channel_summaries as unknown as Record<string, unknown>[]}
              columns={['name', 'category', 'connection_status']}
              columnLabels={{
                name: t('tableColumns.name'),
                category: t('tableColumns.category'),
                connection_status: t('tableColumns.connectionStatus'),
              }}
            />
          </WidgetShell>
        </div>
      )}
    />
  );
}
