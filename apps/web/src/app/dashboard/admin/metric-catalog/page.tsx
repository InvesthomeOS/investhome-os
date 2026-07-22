'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import { fetchWarehouseMetricCatalog, type MetricCatalogEntry } from '@/lib/analytics/warehouse-api';
import { canViewAnalytics } from '@/lib/analytics/bi-permissions';
import { useAuth } from '@/lib/auth/auth-context';

export default function AdminMetricCatalogPage() {
  const t = useTranslations('analytics.dataPlatform');
  const { user } = useAuth();
  const [rows, setRows] = useState<MetricCatalogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('');

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    void fetchWarehouseMetricCatalog(filter || undefined)
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user, filter]);

  if (!canViewAnalytics(user)) {
    return (
      <main className="dashboard">
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </main>
    );
  }

  return (
    <main className="dashboard bi-workspace" data-testid="metric-catalog">
      <header className="bi-workspace__header">
        <div>
          <p className="bi-workspace__eyebrow">{t('eyebrow')}</p>
          <h1 className="bi-workspace__title">{t('catalogTitle')}</h1>
          <p className="bi-workspace__subtitle">{t('catalogSubtitle')}</p>
        </div>
        <select
          className="ih-input"
          value={filter}
          onChange={(e) => {
            setLoading(true);
            setFilter(e.target.value);
          }}
          aria-label={t('certFilter')}
        >
          <option value="">{t('all')}</option>
          <option value="certified">{t('certifiedOnly')}</option>
          <option value="draft">{t('draftOnly')}</option>
        </select>
      </header>
      <nav className="bi-workspace__nav">
        <Link href={'/dashboard/admin/data-platform' as Route} className="bi-workspace__nav-link">
          {t('nav.platform')}
        </Link>
        <Link href={'/dashboard/admin/metric-catalog' as Route} className="bi-workspace__nav-link bi-workspace__nav-link--active">
          {t('nav.catalog')}
        </Link>
      </nav>
      {loading ? <LoadingState label={t('loading')} /> : null}
      {error ? <p className="bi-workspace__empty">{error}</p> : null}
      <section className="ih-panel">
        <div className="ih-panel__body">
          <table className="ih-table">
            <thead>
              <tr>
                <th>{t('metric')}</th>
                <th>{t('domain')}</th>
                <th>{t('status')}</th>
                <th>{t('grain')}</th>
                <th>{t('formula')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-cert={r.certification_status}>
                  <td>{r.metric_key}</td>
                  <td>{r.domain}</td>
                  <td>{r.certification_status}</td>
                  <td>{r.grain}</td>
                  <td>{r.formula}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
