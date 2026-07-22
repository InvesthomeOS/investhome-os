'use client';

import { marketingQueries } from '@/lib/query/marketing-queries';

import { StatusGrid, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function TrackingDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="tracking.title"
      subtitleKey="tracking.subtitle"
      queryOptions={marketingQueries.dashboardTrackingHealth()}
      render={(data, t) => (
        <WidgetShell title={t('tracking.title')} state="ready">
          <StatusGrid items={data.categories} />
        </WidgetShell>
      )}
    />
  );
}
