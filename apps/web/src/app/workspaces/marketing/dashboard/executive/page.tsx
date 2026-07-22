'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { useAuth } from '@/lib/auth/auth-context';
import { resolveMarketingMetricLabel } from '@/lib/marketing/marketing-i18n';
import { canViewMarketingDashboard } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useMarketingDashboardStore } from '@/workspaces/marketing/stores/dashboard-ui-store';

import {
  AlertPanel,
  FunnelWidget,
  MetricRow,
  RecommendationPanel,
  StatusGrid,
  TableWidget,
  TimeFilterBar,
  WidgetShell,
} from '../_components/analytics-widgets';
import { DashboardPageShell } from '../_components/dashboard-shell';

export default function ExecutiveDashboardPage() {
  const t = useTranslations('marketing.analytics');
  const tCommon = useTranslations('common');
  const { user, loading: authLoading } = useAuth();
  const canView = canViewMarketingDashboard(user);
  const timeFilter = useMarketingDashboardStore((s) => s.timeFilter);
  const setTimeFilter = useMarketingDashboardStore((s) => s.setTimeFilter);
  const collapsedWidgets = useMarketingDashboardStore((s) => s.collapsedWidgets);
  const toggleWidgetCollapse = useMarketingDashboardStore((s) => s.toggleWidgetCollapse);

  const query = useQuery({
    ...marketingQueries.dashboardExecutive({ preset: timeFilter.preset, timezone: timeFilter.timezone }),
    enabled: !authLoading && canView,
  });

  if (authLoading) {
    return (
      <DashboardPageShell title={t('executive.title')} subtitle={t('executive.subtitle')}>
        <LoadingState label={tCommon('loading')} />
      </DashboardPageShell>
    );
  }

  if (!canView) {
    return (
      <DashboardPageShell title={t('executive.title')} subtitle={t('executive.subtitle')}>
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </DashboardPageShell>
    );
  }

  if (query.isLoading) {
    return (
      <DashboardPageShell title={t('executive.title')} subtitle={t('executive.subtitle')}>
        <LoadingState label={tCommon('loading')} />
      </DashboardPageShell>
    );
  }

  if (query.isError || !query.data) {
    return (
      <DashboardPageShell title={t('executive.title')} subtitle={t('executive.subtitle')}>
        <ErrorState
          title={t('loadFailed')}
          message={query.error?.message ?? t('loadFailed')}
          action={
            <Button type="button" onClick={() => void query.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      </DashboardPageShell>
    );
  }

  const data = query.data;

  return (
    <DashboardPageShell title={t('executive.title')} subtitle={t('executive.subtitle')}>
      <TimeFilterBar value={timeFilter.preset} onChange={(preset) => setTimeFilter({ preset: preset as typeof timeFilter.preset })} />

      <WidgetShell
        title={t('sections.kpiBar')}
        state="ready"
        collapsed={collapsedWidgets.has('kpi_bar')}
        onToggleCollapse={() => toggleWidgetCollapse('kpi_bar')}
        onRefresh={() => void query.refetch()}
      >
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

      <div className="mkt-analytics-grid">
        <WidgetShell
          title={t('sections.funnel')}
          state="ready"
          collapsed={collapsedWidgets.has('funnel')}
          onToggleCollapse={() => toggleWidgetCollapse('funnel')}
        >
          <FunnelWidget stages={data.funnel.stages} />
        </WidgetShell>

        <WidgetShell
          title={t('sections.health')}
          state="ready"
          collapsed={collapsedWidgets.has('health')}
          onToggleCollapse={() => toggleWidgetCollapse('health')}
        >
          <StatusGrid items={data.health.categories} />
        </WidgetShell>

        <WidgetShell
          title={t('sections.campaigns')}
          state={data.active_campaigns.length > 0 ? 'ready' : 'empty'}
          collapsed={collapsedWidgets.has('campaigns')}
          onToggleCollapse={() => toggleWidgetCollapse('campaigns')}
        >
          <TableWidget
            rows={data.active_campaigns as unknown as Record<string, unknown>[]}
            columns={['name', 'status']}
          />
        </WidgetShell>

        <WidgetShell
          title={t('sections.channels')}
          state={data.channel_summaries.length > 0 ? 'ready' : 'empty'}
          collapsed={collapsedWidgets.has('channels')}
          onToggleCollapse={() => toggleWidgetCollapse('channels')}
        >
          <TableWidget
            rows={data.channel_summaries as unknown as Record<string, unknown>[]}
            columns={['name', 'connection_status']}
          />
        </WidgetShell>

        <WidgetShell
          title={t('sections.alerts')}
          state={data.alerts.length > 0 ? 'ready' : 'empty'}
          collapsed={collapsedWidgets.has('alerts')}
          onToggleCollapse={() => toggleWidgetCollapse('alerts')}
        >
          <AlertPanel alerts={data.alerts} />
        </WidgetShell>

        <WidgetShell
          title={t('sections.recommendations')}
          state={data.recommendations.length > 0 ? 'ready' : 'empty'}
          collapsed={collapsedWidgets.has('recommendations')}
          onToggleCollapse={() => toggleWidgetCollapse('recommendations')}
        >
          <RecommendationPanel items={data.recommendations} />
        </WidgetShell>
      </div>
    </DashboardPageShell>
  );
}
