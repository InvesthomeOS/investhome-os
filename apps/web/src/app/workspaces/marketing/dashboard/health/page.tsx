'use client';

import { marketingQueries } from '@/lib/query/marketing-queries';

import { StatusGrid, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function HealthDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="health.title"
      subtitleKey="health.subtitle"
      queryOptions={marketingQueries.dashboardHealth()}
      render={(data, t) => (
        <div className="mkt-analytics-grid">
          <WidgetShell title={t('sections.health')} state="ready">
            <p className={`mkt-health-overall mkt-health-overall--${data.overall_status}`}>{data.overall_status}</p>
            <StatusGrid items={data.categories} />
          </WidgetShell>
        </div>
      )}
    />
  );
}
