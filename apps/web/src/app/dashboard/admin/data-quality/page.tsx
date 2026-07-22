'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import { fetchWarehouseDq, runWarehouseDq, type DqCheck } from '@/lib/analytics/warehouse-api';
import { canManageAnalytics } from '@/lib/analytics/bi-permissions';
import { useAuth } from '@/lib/auth/auth-context';

export default function AdminDataQualityPage() {
  const t = useTranslations('analytics.dataPlatform');
  const { user } = useAuth();
  const [rows, setRows] = useState<DqCheck[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canManageAnalytics(user)) {
      setLoading(false);
      return;
    }
    void fetchWarehouseDq()
      .then(setRows)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  if (!canManageAnalytics(user)) {
    return (
      <main className="dashboard" data-testid="data-quality-denied">
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </main>
    );
  }

  return (
    <main className="dashboard bi-workspace" data-testid="admin-data-quality">
      <header className="bi-workspace__header">
        <div>
          <p className="bi-workspace__eyebrow">{t('eyebrow')}</p>
          <h1 className="bi-workspace__title">{t('dqTitle')}</h1>
          <p className="bi-workspace__subtitle">{t('dqSubtitle')}</p>
        </div>
        <button
          type="button"
          className="ih-btn ih-btn--primary"
          data-testid="run-dq-suite"
          onClick={() => {
            setLoading(true);
            void runWarehouseDq()
              .then(setRows)
              .catch((err: Error) => setError(err.message))
              .finally(() => setLoading(false));
          }}
        >
          {t('runDq')}
        </button>
      </header>
      <nav className="bi-workspace__nav">
        <Link href={'/dashboard/admin/data-platform' as Route} className="bi-workspace__nav-link">
          {t('nav.platform')}
        </Link>
        <Link href={'/dashboard/admin/data-quality' as Route} className="bi-workspace__nav-link bi-workspace__nav-link--active">
          {t('nav.dq')}
        </Link>
      </nav>
      {loading ? <LoadingState label={t('loading')} /> : null}
      {error ? <p className="bi-workspace__empty">{error}</p> : null}
      <section className="ih-panel">
        <div className="ih-panel__body">
          <table className="ih-table">
            <thead>
              <tr>
                <th>{t('check')}</th>
                <th>{t('domain')}</th>
                <th>{t('status')}</th>
                <th>{t('expected')}</th>
                <th>{t('actual')}</th>
                <th>{t('message')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} data-status={r.status}>
                  <td>{r.check_key}</td>
                  <td>{r.domain}</td>
                  <td>{r.status}</td>
                  <td>{r.expected_value ?? '—'}</td>
                  <td>{r.actual_value ?? '—'}</td>
                  <td>{r.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && !loading ? <p className="bi-workspace__empty">{t('noDq')}</p> : null}
        </div>
      </section>
    </main>
  );
}
