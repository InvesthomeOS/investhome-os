'use client';

import { useCallback, useEffect, useState, useTransition } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import {
  fetchIngestionRuns,
  fetchPlatformOverview,
  fetchReconciliation,
  triggerIngestion,
  type IngestionRun,
  type PlatformOverview,
  type ReconResponse,
} from '@/lib/analytics/warehouse-api';
import { canManageAnalytics } from '@/lib/analytics/bi-permissions';
import { useAuth } from '@/lib/auth/auth-context';

export function DataPlatformWorkspace() {
  const t = useTranslations('analytics.dataPlatform');
  const { user } = useAuth();
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [runs, setRuns] = useState<IngestionRun[]>([]);
  const [recon, setRecon] = useState<ReconResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, startTransition] = useTransition();

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([fetchPlatformOverview(), fetchIngestionRuns(), fetchReconciliation()])
      .then(([ov, runList, rec]) => {
        startTransition(() => {
          setOverview(ov);
          setRuns(runList);
          setRecon(rec);
          setLoading(false);
        });
      })
      .catch((err: Error) => {
        setError(err.message || 'error');
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!canManageAnalytics(user)) {
      setLoading(false);
      return;
    }
    load();
  }, [user, load]);

  if (!canManageAnalytics(user)) {
    return (
      <main className="dashboard" data-testid="data-platform-denied">
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </main>
    );
  }

  return (
    <main className="dashboard bi-workspace" data-testid="data-platform">
      <header className="bi-workspace__header">
        <div>
          <p className="bi-workspace__eyebrow">{t('eyebrow')}</p>
          <h1 className="bi-workspace__title">{t('title')}</h1>
          <p className="bi-workspace__subtitle">{t('subtitle')}</p>
        </div>
        <div className="bi-workspace__actions">
          <button
            type="button"
            className="ih-btn ih-btn--primary"
            disabled={pending}
            data-testid="data-platform-run-ingestion"
            onClick={() => {
              void triggerIngestion('incremental')
                .then(() => load())
                .catch((err: Error) => setError(err.message));
            }}
          >
            {t('runIncremental')}
          </button>
          <button
            type="button"
            className="ih-btn ih-btn--secondary"
            disabled={pending}
            onClick={() => {
              void triggerIngestion('full_refresh')
                .then(() => load())
                .catch((err: Error) => setError(err.message));
            }}
          >
            {t('runFull')}
          </button>
        </div>
      </header>

      <nav className="bi-workspace__nav" aria-label={t('adminNav')}>
        {(
          [
            ['/dashboard/admin/data-platform', 'platform'],
            ['/dashboard/admin/data-quality', 'dq'],
            ['/dashboard/admin/metric-catalog', 'catalog'],
            ['/dashboard/admin/data-lineage', 'lineage'],
          ] as const
        ).map(([href, key]) => (
          <Link key={href} href={href as Route} className="bi-workspace__nav-link">
            {t(`nav.${key}`)}
          </Link>
        ))}
      </nav>

      {loading ? <LoadingState label={t('loading')} /> : null}
      {error ? <p className="bi-workspace__empty">{error}</p> : null}

      {overview ? (
        <section className="ih-panel" data-testid="data-platform-overview">
          <div className="ih-panel__body">
            <h2>{t('overviewHeading')}</h2>
            <dl className="bi-workspace__meta">
              <div>
                <dt>{t('schema')}</dt>
                <dd>{overview.schema_name}</dd>
              </div>
              <div>
                <dt>{t('isolation')}</dt>
                <dd>{overview.isolation}</dd>
              </div>
              <div>
                <dt>{t('oltpReplaced')}</dt>
                <dd>{overview.oltp_queries_replaced ? t('yes') : t('no')}</dd>
              </div>
              <div>
                <dt>{t('currencies')}</dt>
                <dd>{overview.supported_currencies.join(', ')}</dd>
              </div>
              <div>
                <dt>{t('reportingCcy')}</dt>
                <dd>{overview.reporting_currencies.join(', ')}</dd>
              </div>
              <div>
                <dt>{t('timezones')}</dt>
                <dd>{overview.reporting_timezones.join(', ')}</dd>
              </div>
              <div>
                <dt>{t('lastStatus')}</dt>
                <dd data-testid="data-platform-last-status">{overview.last_run.status ?? '—'}</dd>
              </div>
              <div>
                <dt>{t('certified')}</dt>
                <dd>
                  {overview.metric_catalog.certified} / draft {overview.metric_catalog.draft}
                </dd>
              </div>
              <div>
                <dt>{t('costEstimate')}</dt>
                <dd>
                  ~${String(overview.cost_estimate_monthly_usd.estimated_infra_usd ?? '—')} / mo
                </dd>
              </div>
            </dl>
            <p className="bi-workspace__subtitle">{t('isolationNote')}</p>
          </div>
        </section>
      ) : null}

      {recon ? (
        <section className="ih-panel" data-testid="data-platform-recon">
          <div className="ih-panel__body">
            <h2>
              {t('reconHeading')} — {recon.overall}
            </h2>
            <table className="ih-table">
              <thead>
                <tr>
                  <th>{t('metric')}</th>
                  <th>{t('domain')}</th>
                  <th>OLTP</th>
                  <th>WH</th>
                  <th>{t('status')}</th>
                </tr>
              </thead>
              <tbody>
                {recon.checks.map((c) => (
                  <tr key={c.metric_key}>
                    <td>{c.metric_key}</td>
                    <td>{c.domain}</td>
                    <td>{c.oltp_value ?? '—'}</td>
                    <td>{c.warehouse_value ?? '—'}</td>
                    <td>{c.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="ih-panel" data-testid="data-platform-runs">
        <div className="ih-panel__body">
          <h2>{t('runsHeading')}</h2>
          <table className="ih-table">
            <thead>
              <tr>
                <th>{t('status')}</th>
                <th>{t('mode')}</th>
                <th>{t('written')}</th>
                <th>{t('rejected')}</th>
                <th>{t('finished')}</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} data-status={r.status}>
                  <td>{r.status}</td>
                  <td>{r.mode}</td>
                  <td>{r.rows_written}</td>
                  <td>{r.rows_rejected}</td>
                  <td>{r.finished_at ? new Date(r.finished_at).toLocaleString() : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {runs.length === 0 ? <p className="bi-workspace__empty">{t('noRuns')}</p> : null}
        </div>
      </section>
    </main>
  );
}
