'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { relationshipQueries } from '@/workspaces/crm/hooks/use-relationships';
import { getScoreBandBg, getScoreBandColor } from '@/workspaces/crm/stores/relationship-graph-ui-store';

export function RelationshipIntelligenceDashboard() {
  const t = useTranslations('crm.relationships.intelligence');
  const tCommon = useTranslations('common');
  const { authLoading, canRead } = useCrmAccess();

  const dashboardQuery = useQuery({
    ...relationshipQueries.intelligence(),
    enabled: !authLoading && canRead,
  });

  const recommendationsQuery = useQuery({
    ...relationshipQueries.recommendations(),
    enabled: !authLoading && canRead,
  });

  if (authLoading) return <LoadingState label={tCommon('loading')} />;
  if (!canRead) return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;
  if (dashboardQuery.isLoading) return <LoadingState label={t('loading')} />;
  if (dashboardQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={dashboardQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void dashboardQuery.refetch()}>
            {t('loadFailed')}
          </Button>
        }
      />
    );
  }

  const data = dashboardQuery.data;
  const isEmpty = (data?.total_relationships ?? 0) === 0;

  return (
    <div className="crm-intelligence-dashboard">
      <header className="crm-workspace-header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('description')}</p>
        </div>
        <div className="crm-workspace-actions">
          <Link href="/workspaces/crm/relationships">
            <Button variant="secondary">{t('backToList')}</Button>
          </Link>
          <Link href="/workspaces/crm/relationships/network">
            <Button variant="secondary">{t('networkView')}</Button>
          </Link>
        </div>
      </header>

      {isEmpty ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <>
          <div className="crm-intelligence-kpis">
            <div className="crm-kpi-card">
              <span className="crm-kpi-label">{t('totalRelationships')}</span>
              <span className="crm-kpi-value">{data?.total_relationships}</span>
            </div>
            <div className="crm-kpi-card">
              <span className="crm-kpi-label">{t('activeRelationships')}</span>
              <span className="crm-kpi-value">{data?.active_relationships}</span>
            </div>
            <div className="crm-kpi-card">
              <span className="crm-kpi-label">{t('averageScore')}</span>
              <span
                className="crm-kpi-value"
                style={{ color: getScoreBandColor(data?.average_score ?? 0) }}
              >
                {data?.average_score}
              </span>
            </div>
            <div className="crm-kpi-card">
              <span className="crm-kpi-label">{t('atRisk')}</span>
              <span className="crm-kpi-value" style={{ color: 'var(--danger)' }}>
                {data?.at_risk_count}
              </span>
            </div>
            <div className="crm-kpi-card">
              <span className="crm-kpi-label">{t('stale')}</span>
              <span className="crm-kpi-value" style={{ color: 'var(--warning)' }}>
                {data?.stale_count}
              </span>
            </div>
            <div className="crm-kpi-card">
              <span className="crm-kpi-label">{t('openAlerts')}</span>
              <span className="crm-kpi-value">{data?.open_alerts}</span>
            </div>
          </div>

          <div className="crm-intelligence-grid">
            <section className="crm-intelligence-section">
              <h2>{t('scoreDistribution')}</h2>
              <ul className="crm-distribution-list">
                {Object.entries(data?.score_distribution ?? {}).map(([band, count]) => (
                  <li key={band}>
                    <span>{band}</span>
                    <div className="crm-distribution-bar">
                      <div
                        style={{
                          width: `${Math.min(100, (count / (data?.total_relationships || 1)) * 100)}%`,
                          background: getScoreBandBg(Number(band.split('-')[0]) || 0),
                        }}
                      />
                    </div>
                    <span>{count}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="crm-intelligence-section">
              <h2>{t('categoryBreakdown')}</h2>
              <ul>
                {Object.entries(data?.category_breakdown ?? {}).map(([cat, count]) => (
                  <li key={cat}>
                    {cat}: {count}
                  </li>
                ))}
              </ul>
            </section>

            <section className="crm-intelligence-section">
              <h2>{t('topInfluencers')}</h2>
              {data?.top_influencers?.length ? (
                <ul>
                  {data.top_influencers.map((inf) => (
                    <li key={`${inf.entity_type}:${inf.entity_id}`}>
                      {inf.display_name ?? inf.entity_id.slice(0, 8)} ({inf.entity_type})
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{t('noInfluencers')}</p>
              )}
            </section>

            <section className="crm-intelligence-section">
              <h2>{t('recommendations')}</h2>
              {recommendationsQuery.data?.length ? (
                <ul>
                  {recommendationsQuery.data.map((rec) => (
                    <li key={rec.id}>
                      <strong>{rec.title}</strong>
                      <p>{rec.description}</p>
                      <small>{rec.reason}</small>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>{t('noRecommendations')}</p>
              )}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
