'use client';

import { marketingQueries } from '@/lib/query/marketing-queries';

import { TableWidget, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function ProjectsDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="projects.title"
      subtitleKey="projects.subtitle"
      queryOptions={marketingQueries.dashboardExecutive()}
      render={(data, t) => (
        <WidgetShell title={t('projects.title')} state={data.active_campaigns.length ? 'ready' : 'empty'}>
          <TableWidget
            rows={data.active_campaigns as unknown as Record<string, unknown>[]}
            columns={['name', 'status']}
            columnLabels={{
              name: t('tableColumns.name'),
              status: t('tableColumns.status'),
            }}
          />
        </WidgetShell>
      )}
    />
  );
}
