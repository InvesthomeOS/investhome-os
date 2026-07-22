'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canViewMarketingAI } from '@/lib/marketing/marketing-permissions';
import { marketingQueries } from '@/lib/query/marketing-queries';
import { useAuth } from '@/lib/auth/auth-context';

import {
  AIPageShell,
  AIDashboardSkeleton,
  AIConfidenceBadge,
  AIEmptyState,
} from '../_components/ai-shell';

export default function MarketingAIDashboardPage() {
  const t = useTranslations('marketing.ai.dashboard');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const canView = canViewMarketingAI(user);

  const dashboardQuery = useQuery({
    ...marketingQueries.aiDashboard(),
    enabled: canView,
  });

  if (!canView) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </AIPageShell>
    );
  }

  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      {dashboardQuery.isLoading ? (
        <AIDashboardSkeleton />
      ) : dashboardQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={dashboardQuery.error?.message}
          action={
            <Button type="button" onClick={() => void dashboardQuery.refetch()}>
              {tCommon('retry')}
            </Button>
          }
        />
      ) : dashboardQuery.data ? (
        <div className="mkt-ai-dashboard">
          <section className="mkt-ai-panel mkt-ai-panel--summary">
            <h2>{t('executiveSummary')}</h2>
            <p>{dashboardQuery.data.executive_summary}</p>
          </section>

          <div className="mkt-ai-dashboard__grid">
            <section className="mkt-ai-panel">
              <div className="mkt-ai-panel__header">
                <h2>{t('marketingHealth')}</h2>
                <AIConfidenceBadge confidence={dashboardQuery.data.marketing_health.confidence} />
              </div>
              <p className="mkt-ai-panel__status">{dashboardQuery.data.marketing_health.overall_status}</p>
            </section>

            <section className="mkt-ai-panel">
              <div className="mkt-ai-panel__header">
                <h2>{t('predictionConfidence')}</h2>
                <AIConfidenceBadge confidence={dashboardQuery.data.prediction_confidence.confidence} />
              </div>
              <p>{t('unknownModel')}</p>
            </section>

            <section className="mkt-ai-panel">
              <div className="mkt-ai-panel__header">
                <h2>{t('leadQuality')}</h2>
                <AIConfidenceBadge confidence={dashboardQuery.data.lead_quality.confidence} />
              </div>
              <p>{t('unknown')}</p>
            </section>
          </div>

          <section className="mkt-ai-panel">
            <h2>{t('criticalInsights')}</h2>
            {dashboardQuery.data.critical_insights.length === 0 ? (
              <AIEmptyState title={t('noInsights')} description={t('noInsightsHint')} />
            ) : (
              <ul className="mkt-ai-list">
                {dashboardQuery.data.critical_insights.map((insight) => (
                  <li key={insight.id} className={`mkt-ai-list__item mkt-ai-list__item--${insight.severity}`}>
                    <strong>{insight.title}</strong>
                    <p>{insight.summary}</p>
                    <AIConfidenceBadge confidence={insight.confidence} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="mkt-ai-dashboard__split">
            <section className="mkt-ai-panel">
              <h2>{t('campaignRecommendations')}</h2>
              {dashboardQuery.data.campaign_recommendations.length === 0 ? (
                <AIEmptyState title={t('noRecommendations')} description={t('noRecommendationsHint')} />
              ) : (
                <ul className="mkt-ai-list">
                  {dashboardQuery.data.campaign_recommendations.map((rec) => (
                    <li key={rec.id} className="mkt-ai-list__item">
                      <strong>{rec.title}</strong>
                      <p>{rec.rationale}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="mkt-ai-panel">
              <h2>{t('anomalyAlerts')}</h2>
              {dashboardQuery.data.anomaly_alerts.length === 0 ? (
                <AIEmptyState title={t('noAnomalies')} description={t('noAnomaliesHint')} />
              ) : (
                <ul className="mkt-ai-list">
                  {dashboardQuery.data.anomaly_alerts.map((a) => (
                    <li key={a.id} className="mkt-ai-list__item">
                      <strong>{a.title}</strong>
                      <p>{a.description}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <section className="mkt-ai-panel mkt-ai-panel--briefing">
            <div className="mkt-ai-panel__header">
              <h2>{t('executiveBriefing')}</h2>
              <AIConfidenceBadge confidence={dashboardQuery.data.executive_briefing.confidence} />
            </div>
            <p>{dashboardQuery.data.executive_briefing.summary}</p>
          </section>
        </div>
      ) : null}
    </AIPageShell>
  );
}
