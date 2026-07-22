'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';
import { Sparkline } from '@/components/design-system/charts/Sparkline';

import { exploreDataset, type ExploreResponse } from '@/lib/analytics/warehouse-api';
import { canViewAnalytics } from '@/lib/analytics/bi-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { BiWorkspaceShell } from '../_components/bi-workspace-shell';

export default function AnalyticsPortfolioPage() {
  const t = useTranslations('analytics');
  const { user } = useAuth();
  const [data, setData] = useState<ExploreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    void exploreDataset('executive_daily')
      .then(setData)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  const spark = (data?.rows ?? [])
    .slice()
    .reverse()
    .map((r) => Number(r.pipeline_open ?? 0))
    .filter((n) => !Number.isNaN(n));

  return (
    <BiWorkspaceShell
      title={t('pages.portfolio.title')}
      subtitle={t('pages.portfolio.subtitle')}
    >
      <div data-testid="analytics-portfolio">
        {loading ? <LoadingState label={t('states.loading')} /> : null}
        {error ? <p className="bi-workspace__empty">{error}</p> : null}
        {!loading && !error ? (
          <section className="ih-panel">
            <div className="ih-panel__body">
              <h2>{t('pages.portfolio.martHeading')}</h2>
              <p className="bi-workspace__subtitle">{t('pages.portfolio.martNote')}</p>
              {spark.length > 1 ? (
                <div style={{ maxWidth: 420, marginBlock: '1rem' }}>
                  <Sparkline values={spark} ariaLabel={t('pages.portfolio.pipelineSpark')} />
                </div>
              ) : null}
              <table className="ih-table">
                <thead>
                  <tr>
                    <th>{t('pages.portfolio.date')}</th>
                    <th>{t('pages.portfolio.ccy')}</th>
                    <th>{t('pages.portfolio.cash')}</th>
                    <th>{t('pages.portfolio.pipeline')}</th>
                    <th>{t('pages.portfolio.investors')}</th>
                    <th>{t('pages.portfolio.projects')}</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.rows ?? []).map((r, idx) => (
                    <tr key={`${r.snapshot_date}-${r.reporting_currency}-${idx}`}>
                      <td>{String(r.snapshot_date ?? '')}</td>
                      <td>{String(r.reporting_currency ?? '')}</td>
                      <td>{String(r.cash_balance ?? '—')}</td>
                      <td>{String(r.pipeline_open ?? '—')}</td>
                      <td>{String(r.active_investors ?? '—')}</td>
                      <td>{String(r.project_count ?? '—')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(data?.rows?.length ?? 0) === 0 ? (
                <p className="bi-workspace__empty">{t('pages.portfolio.empty')}</p>
              ) : null}
            </div>
          </section>
        ) : null}
      </div>
    </BiWorkspaceShell>
  );
}
