'use client';

import { resolveMarketingMetricLabel } from '@/lib/marketing/marketing-i18n';
import { marketingQueries } from '@/lib/query/marketing-queries';

import { MetricRow, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function AudiencesDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="audiences.title"
      subtitleKey="audiences.subtitle"
      queryOptions={marketingQueries.dashboardKPIs()}
      render={(data, t) => (
        <WidgetShell title={t('audiences.title')} state="ready">
          <MetricRow
            metrics={data.kpis
              .filter((k) => ['marketing_leads', 'qualified_leads', 'conversion_rate'].includes(k.key))
              .map((k) => ({
                label: resolveMarketingMetricLabel(t, k.key, k.label),
                value: typeof k.value === 'number' || typeof k.value === 'string' ? k.value : null,
                unit: k.unit,
                state: k.state,
                evidence: k.evidence,
              }))}
          />
        </WidgetShell>
      )}
    />
  );
}
