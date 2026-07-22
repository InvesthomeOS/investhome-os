'use client';

import { marketingQueries } from '@/lib/query/marketing-queries';

import { FunnelWidget, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function FunnelDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="funnel.title"
      subtitleKey="funnel.subtitle"
      queryOptions={marketingQueries.dashboardFunnel()}
      render={(data, t) => (
        <WidgetShell title={t('sections.funnel')} state="ready">
          <FunnelWidget stages={data.stages} />
        </WidgetShell>
      )}
    />
  );
}
