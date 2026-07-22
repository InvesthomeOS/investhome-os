'use client';

import { marketingQueries } from '@/lib/query/marketing-queries';

import { WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';
import { WidgetDataDisplay } from '../../_components/widget-data-display';

export default function WidgetsDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="widgets.title"
      subtitleKey="widgets.subtitle"
      queryOptions={marketingQueries.dashboardWidgets()}
      render={(data) => (
        <div className="mkt-analytics-grid">
          {data.widgets.map((widget) => (
            <WidgetShell key={widget.key} title={widget.title} subtitle={widget.subtitle ?? undefined} state={widget.state as 'ready' | 'empty'}>
              {widget.data ? <WidgetDataDisplay data={widget.data as Record<string, unknown>} /> : null}
            </WidgetShell>
          ))}
        </div>
      )}
    />
  );
}
