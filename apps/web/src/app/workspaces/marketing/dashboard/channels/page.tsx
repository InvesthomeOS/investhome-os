'use client';

import { marketingQueries } from '@/lib/query/marketing-queries';

import { TableWidget, WidgetShell } from '../_components/analytics-widgets';
import { AnalyticsSectionPage } from '../_components/analytics-section-page';

export default function ChannelsDashboardPage() {
  return (
    <AnalyticsSectionPage
      titleKey="channels.title"
      subtitleKey="channels.subtitle"
      queryOptions={marketingQueries.dashboardExecutive()}
      render={(data, t) => (
        <WidgetShell title={t('channels.title')} state={data.channel_summaries.length ? 'ready' : 'empty'}>
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
      )}
    />
  );
}
