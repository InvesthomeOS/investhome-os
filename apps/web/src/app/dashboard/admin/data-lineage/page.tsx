'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import { fetchLineage, type LineageEdge } from '@/lib/analytics/warehouse-api';
import { canManageAnalytics } from '@/lib/analytics/bi-permissions';
import { useAuth } from '@/lib/auth/auth-context';

export default function AdminDataLineagePage() {
  const t = useTranslations('analytics.dataPlatform');
  const { user } = useAuth();
  const [edges, setEdges] = useState<LineageEdge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canManageAnalytics(user)) {
      setLoading(false);
      return;
    }
    void fetchLineage()
      .then(setEdges)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  if (!canManageAnalytics(user)) {
    return (
      <main className="dashboard">
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </main>
    );
  }

  return (
    <main className="dashboard bi-workspace" data-testid="data-lineage">
      <header className="bi-workspace__header">
        <div>
          <p className="bi-workspace__eyebrow">{t('eyebrow')}</p>
          <h1 className="bi-workspace__title">{t('lineageTitle')}</h1>
          <p className="bi-workspace__subtitle">{t('lineageSubtitle')}</p>
        </div>
      </header>
      <nav className="bi-workspace__nav">
        <Link href={'/dashboard/admin/data-platform' as Route} className="bi-workspace__nav-link">
          {t('nav.platform')}
        </Link>
        <Link href={'/dashboard/admin/data-lineage' as Route} className="bi-workspace__nav-link bi-workspace__nav-link--active">
          {t('nav.lineage')}
        </Link>
      </nav>
      {loading ? <LoadingState label={t('loading')} /> : null}
      {error ? <p className="bi-workspace__empty">{error}</p> : null}
      <section className="ih-panel">
        <div className="ih-panel__body">
          <table className="ih-table">
            <thead>
              <tr>
                <th>{t('source')}</th>
                <th>{t('relation')}</th>
                <th>{t('target')}</th>
                <th>{t('domain')}</th>
              </tr>
            </thead>
            <tbody>
              {edges.map((e) => (
                <tr key={e.id}>
                  <td>{e.source_object}</td>
                  <td>{e.relation}</td>
                  <td>{e.target_object}</td>
                  <td>{e.domain ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {edges.length === 0 && !loading ? <p className="bi-workspace__empty">{t('noLineage')}</p> : null}
        </div>
      </section>
    </main>
  );
}
