'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Card, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import { marketingLabelKey } from '@/lib/marketing/marketing-i18n';
import { canViewMarketingDashboard } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';
import type { DashboardWidgetState, MarketingDashboardWidget } from '@/workspaces/marketing/types';

import { WidgetDataDisplay } from './widget-data-display';

const QUICK_ACTION_MARK: Record<string, string> = {
  create_campaign: 'K',
  create_audience: 'A',
  create_segment: 'S',
  create_lead_source: 'L',
  create_landing_page: 'P',
  create_form: 'F',
  create_content: 'İ',
  schedule_social: 'So',
  email_campaign: 'E',
  whatsapp_campaign: 'W',
  create_event: 'Et',
  upload_asset: 'V',
  request_approval: 'O',
  add_budget: 'B',
  open_calendar: 'T',
  open_analytics: 'An',
};

function WidgetBody({ state, data }: { state: DashboardWidgetState; data: MarketingDashboardWidget['data'] }) {
  const t = useTranslations('marketing.dashboard.widgetStates');
  const tCommon = useTranslations('marketing');

  if (state === 'loading') {
    return <LoadingState label={t('loading')} />;
  }

  if (state === 'ready' && data) {
    return <WidgetDataDisplay data={data} emptyLabel={t('empty')} />;
  }

  if (state === 'not_connected') {
    return (
      <EmptyState title={tCommon('notConnectedTitle')} description={tCommon('notConnectedDescription')} />
    );
  }

  if (state === 'permission_restricted') {
    return (
      <EmptyState
        title={tCommon('permissionRestrictedTitle')}
        description={tCommon('permissionRestrictedDescription')}
      />
    );
  }

  if (state === 'error') {
    return <EmptyState title={t('error')} />;
  }

  // Keep empty-state copy short inside dense widget cards; avoid repeating
  // the long provider/setup sentence across the full landing grid.
  return <EmptyState title={t('empty')} />;
}

function DashboardWidget({ widget }: { widget: MarketingDashboardWidget }) {
  const t = useTranslations('marketing.dashboard.widgets');
  return (
    <Card title={t(widget.key as 'executive_summary')}>
      <div className="marketing-dashboard__widget-body">
        <WidgetBody state={widget.state} data={widget.data} />
      </div>
    </Card>
  );
}

export function MarketingDashboard() {
  const t = useTranslations('marketing');
  const tCommon = useTranslations('common');
  const tOverview = useTranslations('marketing.workspaceOverview');
  const tCampaignStatus = useTranslations('marketing.campaignStatuses');
  const tConnectionStatus = useTranslations('marketing.connectionStatuses');
  const { user, loading: authLoading } = useAuth();
  const canView = canViewMarketingDashboard(user);

  const dashboardQuery = useQuery({
    ...marketingQueries.dashboard(),
    enabled: !authLoading && canView,
  });

  const quickActionsQuery = useQuery({
    ...marketingQueries.quickActions(),
    enabled: !authLoading && canView,
  });

  if (authLoading) {
    return (
      <main className="dashboard marketing-dashboard">
        <LoadingState label={tCommon('loading')} />
      </main>
    );
  }

  if (!canView) {
    return (
      <main className="dashboard marketing-dashboard">
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </main>
    );
  }

  if (dashboardQuery.isLoading) {
    return (
      <main className="dashboard marketing-dashboard">
        <LoadingState label={tCommon('loading')} />
      </main>
    );
  }

  if (dashboardQuery.isError) {
    return (
      <main className="dashboard marketing-dashboard">
        <ErrorState
          title={t('loadFailed')}
          message={dashboardQuery.error?.message ?? t('loadFailed')}
          action={
            <Button type="button" onClick={() => void dashboardQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      </main>
    );
  }

  const data = dashboardQuery.data;
  const quickActions = quickActionsQuery.data?.actions ?? [];
  const overview = data?.workspace_overview;

  const campaignStatusLabel = (status: string) =>
    tCampaignStatus.has(status) ? tCampaignStatus(status) : status.replace(/_/g, ' ');

  const connectionStatusLabel = (status: string) =>
    tConnectionStatus.has(status) ? tConnectionStatus(status) : status.replace(/_/g, ' ');

  const formatMetric = (metric?: { value: number | string | null; available: boolean } | null) => {
    if (!metric || !metric.available || metric.value === null || metric.value === undefined) {
      return tOverview('unavailable');
    }
    return String(metric.value);
  };

  return (
    <main className="dashboard marketing-dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('dashboardTitle')}</h1>
        <p className="dashboard__subtitle">{t('dashboardSubtitle')}</p>
      </header>

      <ContextualAiActions module="marketing" />

      {overview ? (
        <section className="marketing-dashboard__section" aria-labelledby="marketing-foundation-kpis-heading">
          <h2 id="marketing-foundation-kpis-heading" className="marketing-dashboard__section-title">
            {tOverview('title')}
          </h2>
          <div className="marketing-summary__grid marketing-dashboard__kpi-grid">
            {(
              [
                ['totalCampaigns', overview.total_campaigns],
                ['activeCampaigns', overview.active_campaigns],
                ['budget', overview.budget],
                ['spend', overview.spend],
                ['estimatedLeads', overview.estimated_leads],
                ['actualLeads', overview.actual_leads],
                ...(overview.qualified_leads ? [['qualifiedLeads', overview.qualified_leads] as const] : []),
                ...(overview.converted_leads ? [['convertedLeads', overview.converted_leads] as const] : []),
                ...(overview.avg_cpl ? [['avgCpl', overview.avg_cpl] as const] : []),
                ...(overview.avg_conversion_rate ? [['avgConversionRate', overview.avg_conversion_rate] as const] : []),
                ...(overview.campaigns_requiring_attention
                  ? [['campaignsRequiringAttention', overview.campaigns_requiring_attention] as const]
                  : []),
                ['estimatedRoi', overview.estimated_roi],
                ['topPerforming', overview.top_performing],
                ['upcoming', overview.upcoming],
              ] as const
            ).map(([key, metric]) => (
              <article key={key} className="marketing-summary__card">
                <p className="marketing-summary__label">{tOverview(key)}</p>
                <p
                  className={
                    metric.available
                      ? 'marketing-summary__value'
                      : 'marketing-summary__value marketing-summary__value--unavailable'
                  }
                >
                  {formatMetric(metric)}
                  {key === 'budget' && overview.currency && metric.available ? ` ${overview.currency}` : ''}
                  {key === 'spend' && overview.currency && metric.available ? ` ${overview.currency}` : ''}
                </p>
              </article>
            ))}
          </div>
          {(overview.upcoming_campaigns?.length ?? 0) > 0 ? (
            <div className="marketing-dashboard__upcoming">
              <h3>{tOverview('upcomingList')}</h3>
              <ul>
                {overview.upcoming_campaigns.map((campaign) => (
                  <li key={campaign.id}>
                    <Link href={`/workspaces/marketing/campaigns/${campaign.id}` as Route}>{campaign.name}</Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      <section className="marketing-dashboard__section" aria-labelledby="marketing-quick-actions-heading">
        <h2 id="marketing-quick-actions-heading" className="marketing-dashboard__section-title">
          {t('quickActions.title')}
        </h2>
        {quickActionsQuery.isLoading ? (
          <LoadingState label={tCommon('loading')} />
        ) : quickActionsQuery.isError ? (
          <EmptyState title={t('loadFailed')} />
        ) : quickActions.length === 0 ? (
          <EmptyState title={t('quickActions.empty')} />
        ) : (
          <div className="marketing-dashboard__quick-actions" role="list">
            {quickActions.map((action) => {
              const label = t(marketingLabelKey(action.label_key) as 'quickActions.createCampaign');
              return (
                <Link
                  key={action.key}
                  href={action.href as Route}
                  className="marketing-dashboard__quick-action"
                  role="listitem"
                >
                  <span className="marketing-dashboard__quick-action-mark" aria-hidden="true">
                    {QUICK_ACTION_MARK[action.key] ?? label.slice(0, 1)}
                  </span>
                  <span className="marketing-dashboard__quick-action-label">{label}</span>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      <section className="marketing-dashboard__section" aria-labelledby="marketing-widgets-heading">
        <h2 id="marketing-widgets-heading" className="marketing-dashboard__section-title">
          {t('dashboard.sections.widgets')}
        </h2>
        {(data?.widgets ?? []).length === 0 ? (
          <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
        ) : (
          <div className="marketing-dashboard__grid">
            {(data?.widgets ?? []).map((widget) => (
              <DashboardWidget key={widget.key} widget={widget} />
            ))}
          </div>
        )}
      </section>

      <section className="marketing-dashboard__section" aria-labelledby="marketing-campaigns-heading">
        <h2 id="marketing-campaigns-heading" className="marketing-dashboard__section-title">
          {t('dashboard.sections.activeCampaigns')}
        </h2>
        {(data?.active_campaigns ?? []).length === 0 ? (
          <EmptyState title={t('emptyCampaigns')} description={t('emptyCampaignsHint')} />
        ) : (
          <div className="marketing-dashboard__grid">
            {data?.active_campaigns.map((campaign) => (
              <Card key={campaign.id} title={campaign.name}>
                <div className="marketing-dashboard__campaign-meta">
                  <StatusChip tone={campaign.status === 'active' ? 'success' : 'info'}>
                    {campaignStatusLabel(campaign.status)}
                  </StatusChip>
                  <span>{campaign.campaign_type.replace(/_/g, ' ')}</span>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="marketing-dashboard__section" aria-labelledby="marketing-providers-heading">
        <h2 id="marketing-providers-heading" className="marketing-dashboard__section-title">
          {t('dashboard.sections.providerStatus')}
        </h2>
        {(data?.provider_statuses ?? []).length === 0 ? (
          <EmptyState title={t('notConnectedTitle')} description={t('notConnectedDescription')} />
        ) : (
          <ul className="marketing-dashboard__provider-list">
            {data?.provider_statuses.map((provider) => (
              <li
                key={provider.channel_id}
                className={`marketing-provider-badge marketing-provider-badge--${provider.connection_status}`}
              >
                <span className="marketing-dashboard__provider-name">{provider.channel_name}</span>
                <StatusChip
                  tone={
                    provider.connection_status === 'connected'
                      ? 'success'
                      : provider.connection_status === 'error'
                        ? 'danger'
                        : 'default'
                  }
                >
                  {connectionStatusLabel(provider.connection_status)}
                </StatusChip>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="marketing-dashboard__section" aria-labelledby="marketing-alerts-heading">
        <h2 id="marketing-alerts-heading" className="marketing-dashboard__section-title">
          {t('dashboard.sections.alerts')}
        </h2>
        {(data?.alerts ?? []).length === 0 ? (
          <EmptyState title={t('emptyAlerts')} description={t('emptyAlertsHint')} />
        ) : (
          <div className="marketing-dashboard__grid">
            {data?.alerts.map((alert) => (
              <Card key={alert.id} title={alert.title}>
                <p className="marketing-dashboard__card-copy">{alert.message ?? alert.severity}</p>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="marketing-dashboard__section" aria-labelledby="marketing-recommendations-heading">
        <h2 id="marketing-recommendations-heading" className="marketing-dashboard__section-title">
          {t('dashboard.sections.recommendations')}
        </h2>
        {(data?.recommendations ?? []).length === 0 ? (
          <EmptyState title={t('emptyRecommendations')} description={t('emptyRecommendationsHint')} />
        ) : (
          <div className="marketing-dashboard__grid">
            {data?.recommendations.map((rec) => (
              <Card key={rec.id} title={rec.title}>
                <p className="marketing-dashboard__card-copy">{rec.rationale ?? rec.description}</p>
              </Card>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
