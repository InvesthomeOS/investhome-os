'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import {
  auditWarehouseExport,
  exploreDataset,
  fetchGovernedDatasets,
  type ExploreResponse,
  type GovernedDataset,
} from '@/lib/analytics/warehouse-api';
import { canExportAnalytics, canViewAnalytics } from '@/lib/analytics/bi-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { BiWorkspaceShell } from '../_components/bi-workspace-shell';

export default function AnalyticsExplorerPage() {
  const t = useTranslations('analytics');
  const { user } = useAuth();
  const [datasets, setDatasets] = useState<GovernedDataset[]>([]);
  const [selected, setSelected] = useState('executive_daily');
  const [result, setResult] = useState<ExploreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    void fetchGovernedDatasets()
      .then((ds) => {
        setDatasets(ds);
        if (ds[0]) setSelected(ds[0].dataset_key);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    if (!selected || !canViewAnalytics(user)) return;
    setLoading(true);
    void exploreDataset(selected)
      .then(setResult)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selected, user]);

  const canExport = canExportAnalytics(user);
  const cols = result?.allowed_columns ?? [];

  return (
    <BiWorkspaceShell
      title={t('pages.explorer.title')}
      subtitle={t('pages.explorer.subtitle')}
      showFilters={false}
      actions={
        canExport ? (
          <button
            type="button"
            className="ih-btn ih-btn--secondary"
            data-testid="explorer-export-audit"
            onClick={() => {
              void auditWarehouseExport(selected, result?.row_count).catch((err: Error) =>
                setError(err.message),
              );
            }}
          >
            {t('pages.explorer.logExport')}
          </button>
        ) : null
      }
    >
      <div data-testid="analytics-explorer">
        <div className="bi-workspace__actions" style={{ marginBottom: '1rem' }}>
          <label>
            {t('pages.explorer.dataset')}{' '}
            <select
              className="ih-input"
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              data-testid="explorer-dataset-select"
            >
              {datasets.map((d) => (
                <option key={d.dataset_key} value={d.dataset_key}>
                  {d.name} ({d.classification})
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="bi-workspace__subtitle">{t('pages.explorer.governedNote')}</p>
        {loading ? <LoadingState label={t('states.loading')} /> : null}
        {error ? <p className="bi-workspace__empty">{error}</p> : null}
        {result && !loading ? (
          <section className="ih-panel">
            <div className="ih-panel__body">
              <p>
                {result.mart_table} · {result.row_count} {t('pages.explorer.rows')}
              </p>
              <table className="ih-table">
                <thead>
                  <tr>
                    {cols.map((c) => (
                      <th key={c}>{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(result.rows ?? []).map((row, idx) => (
                    <tr key={idx}>
                      {cols.map((c) => (
                        <td key={c}>{String(row[c] ?? '—')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </div>
    </BiWorkspaceShell>
  );
}
