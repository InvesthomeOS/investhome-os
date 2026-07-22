'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import { deleteSavedReport, fetchSavedReports } from '@/lib/analytics/bi-api';
import { canViewAnalytics } from '@/lib/analytics/bi-permissions';
import type { BiSavedReport } from '@/lib/analytics/bi-types';
import { useAuth } from '@/lib/auth/auth-context';

import { BiWorkspaceShell } from '../_components/bi-workspace-shell';

export default function AnalyticsReportsPage() {
  const t = useTranslations('analytics');
  const { user } = useAuth();
  const [reports, setReports] = useState<BiSavedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    void fetchSavedReports()
      .then((items) => {
        setReports(items);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [user]);

  if (!canViewAnalytics(user)) {
    return (
      <BiWorkspaceShell title={t('pages.reports.title')} subtitle={t('pages.reports.subtitle')} showFilters={false}>
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </BiWorkspaceShell>
    );
  }

  return (
    <BiWorkspaceShell
      title={t('pages.reports.title')}
      subtitle={t('pages.reports.subtitle')}
      showFilters={false}
      actions={
        <Link href={'/dashboard/analytics/reports/builder' as Route} className="ih-btn ih-btn--primary">
          {t('reports.new')}
        </Link>
      }
    >
      {loading ? <LoadingState label={t('states.loading')} /> : null}
      {error ? <p className="bi-workspace__error">{t('states.error')}</p> : null}
      {!loading && !error && reports.length === 0 ? (
        <div className="ih-panel">
          <div className="ih-panel__body">
            <p className="bi-workspace__empty">{t('reports.empty')}</p>
            <Link href={'/dashboard/analytics/reports/builder' as Route} className="ih-btn ih-btn--secondary">
              {t('reports.new')}
            </Link>
          </div>
        </div>
      ) : null}
      {!loading && reports.length > 0 ? (
        <div className="bi-table-wrap ih-panel">
          <div className="ih-panel__body">
            <table className="bi-table">
              <thead>
                <tr>
                  <th>{t('reports.columns.name')}</th>
                  <th>{t('reports.columns.domain')}</th>
                  <th>{t('reports.columns.chart')}</th>
                  <th>{t('reports.columns.metrics')}</th>
                  <th>{t('reports.columns.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.id}>
                    <td>{report.name}</td>
                    <td>{report.domain}</td>
                    <td>{report.chart_type}</td>
                    <td>{report.metric_keys.join(', ')}</td>
                    <td>
                      <button
                        type="button"
                        className="ih-btn ih-btn--ghost"
                        onClick={async () => {
                          await deleteSavedReport(report.id);
                          setReports((prev) => prev.filter((r) => r.id !== report.id));
                        }}
                      >
                        {t('reports.delete')}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </BiWorkspaceShell>
  );
}
