'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import {
  createAlertThreshold,
  fetchAlertThresholds,
  fetchDataQuality,
  fetchMetricRegistry,
} from '@/lib/analytics/bi-api';
import { canManageAnalytics, canViewAnalytics } from '@/lib/analytics/bi-permissions';
import type { BiAlertThreshold, DataQualityResponse, MetricDefinition } from '@/lib/analytics/bi-types';
import { useAuth } from '@/lib/auth/auth-context';

import { BiWorkspaceShell } from '../_components/bi-workspace-shell';

export default function DataQualityPage() {
  const t = useTranslations('analytics');
  const { user } = useAuth();
  const [data, setData] = useState<DataQualityResponse | null>(null);
  const [thresholds, setThresholds] = useState<BiAlertThreshold[]>([]);
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [metricKey, setMetricKey] = useState('open_risks');
  const [thresholdValue, setThresholdValue] = useState('');
  const [thresholdName, setThresholdName] = useState('');

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    void Promise.all([fetchDataQuality(), fetchAlertThresholds(), fetchMetricRegistry()])
      .then(([dq, th, reg]) => {
        setData(dq);
        setThresholds(th);
        setMetrics(reg);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [user]);

  if (!canViewAnalytics(user)) {
    return (
      <BiWorkspaceShell
        title={t('pages.dataQuality.title')}
        subtitle={t('pages.dataQuality.subtitle')}
        showFilters={false}
      >
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </BiWorkspaceShell>
    );
  }

  return (
    <BiWorkspaceShell
      title={t('pages.dataQuality.title')}
      subtitle={t('pages.dataQuality.subtitle')}
      showFilters={false}
    >
      {loading ? <LoadingState label={t('states.loading')} /> : null}

      {data ? (
        <section className="ih-panel">
          <div className="ih-panel__body">
            <h2 className="bi-section__title">{t('dataQuality.findings')}</h2>
            {data.findings.length === 0 ? (
              <p className="bi-workspace__empty">{t('dataQuality.none')}</p>
            ) : (
              <ul className="bi-dq-list">
                {data.findings.map((f) => (
                  <li key={f.key} className={`bi-dq-list__item bi-dq-list__item--${f.severity}`}>
                    <strong>{f.title}</strong>
                    <span>{f.description}</span>
                    <small>
                      {f.source}
                      {f.metric_keys.length ? ` · ${f.metric_keys.join(', ')}` : ''}
                    </small>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      ) : null}

      <section className="ih-panel">
        <div className="ih-panel__body">
          <h2 className="bi-section__title">{t('alerts.title')}</h2>
          <p className="bi-section__notes">{t('alerts.note')}</p>
          {thresholds.length === 0 ? (
            <p className="bi-workspace__empty">{t('alerts.empty')}</p>
          ) : (
            <table className="bi-table">
              <thead>
                <tr>
                  <th>{t('alerts.columns.name')}</th>
                  <th>{t('alerts.columns.metric')}</th>
                  <th>{t('alerts.columns.rule')}</th>
                  <th>{t('alerts.columns.severity')}</th>
                </tr>
              </thead>
              <tbody>
                {thresholds.map((th) => (
                  <tr key={th.id}>
                    <td>{th.name}</td>
                    <td>{th.metric_key}</td>
                    <td>
                      {th.operator} {th.threshold_value}
                    </td>
                    <td>{th.severity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {canManageAnalytics(user) ? (
            <form
              className="bi-builder__grid"
              style={{ marginTop: '1rem' }}
              onSubmit={async (e) => {
                e.preventDefault();
                if (!thresholdName || !thresholdValue) return;
                const created = await createAlertThreshold({
                  metric_key: metricKey,
                  name: thresholdName,
                  operator: 'gt',
                  threshold_value: thresholdValue,
                  severity: 'warning',
                });
                setThresholds((prev) => [...prev, created]);
                setThresholdName('');
                setThresholdValue('');
              }}
            >
              <label className="bi-filters__field">
                <span>{t('alerts.name')}</span>
                <input value={thresholdName} onChange={(e) => setThresholdName(e.target.value)} />
              </label>
              <label className="bi-filters__field">
                <span>{t('alerts.metric')}</span>
                <select value={metricKey} onChange={(e) => setMetricKey(e.target.value)}>
                  {metrics.map((m) => (
                    <option key={m.key} value={m.key}>
                      {m.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="bi-filters__field">
                <span>{t('alerts.value')}</span>
                <input value={thresholdValue} onChange={(e) => setThresholdValue(e.target.value)} />
              </label>
              <button type="submit" className="ih-btn ih-btn--secondary">
                {t('alerts.add')}
              </button>
            </form>
          ) : null}
        </div>
      </section>
    </BiWorkspaceShell>
  );
}
