'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { LoadingState } from '@investhome/ui';

import { createSavedReport, fetchMetricRegistry } from '@/lib/analytics/bi-api';
import { canViewAnalytics } from '@/lib/analytics/bi-permissions';
import type { BiChartType, MetricDefinition } from '@/lib/analytics/bi-types';
import { useAuth } from '@/lib/auth/auth-context';

import { BiWorkspaceShell } from '../../_components/bi-workspace-shell';

const CHART_TYPES: BiChartType[] = ['line', 'bar', 'area', 'donut', 'funnel', 'kpi', 'table'];

export default function ReportBuilderPage() {
  const t = useTranslations('analytics');
  const { user } = useAuth();
  const router = useRouter();
  const [metrics, setMetrics] = useState<MetricDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [domain, setDomain] = useState('executive');
  const [chartType, setChartType] = useState<BiChartType>('kpi');
  const [selected, setSelected] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    void fetchMetricRegistry()
      .then((items) => {
        setMetrics(items);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [user]);

  if (!canViewAnalytics(user)) {
    return (
      <BiWorkspaceShell title={t('pages.builder.title')} subtitle={t('pages.builder.subtitle')} showFilters={false}>
        <p className="bi-workspace__empty">{t('accessDenied')}</p>
      </BiWorkspaceShell>
    );
  }

  return (
    <BiWorkspaceShell title={t('pages.builder.title')} subtitle={t('pages.builder.subtitle')} showFilters={false}>
      <p className="bi-workspace__ai-label">{t('builder.semanticOnly')}</p>
      {loading ? <LoadingState label={t('states.loading')} /> : null}
      {!loading ? (
        <form
          className="ih-panel bi-builder"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!name.trim() || selected.length === 0) {
              setError(t('builder.validation'));
              return;
            }
            setSaving(true);
            setError(null);
            try {
              await createSavedReport({
                name: name.trim(),
                domain,
                chart_type: chartType,
                metric_keys: selected,
              });
              router.push('/dashboard/analytics/reports' as Route);
            } catch (err) {
              setError(err instanceof Error ? err.message : t('states.error'));
              setSaving(false);
            }
          }}
        >
          <div className="ih-panel__body bi-builder__grid">
            <label className="bi-filters__field">
              <span>{t('builder.name')}</span>
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label className="bi-filters__field">
              <span>{t('builder.domain')}</span>
              <select value={domain} onChange={(e) => setDomain(e.target.value)}>
                {['executive', 'sales', 'marketing', 'investor', 'finance', 'project', 'website', 'operational'].map(
                  (d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label className="bi-filters__field">
              <span>{t('builder.chart')}</span>
              <select value={chartType} onChange={(e) => setChartType(e.target.value as BiChartType)}>
                {CHART_TYPES.map((c) => (
                  <option key={c} value={c}>
                    {t(`builder.chartTypes.${c}`)}
                  </option>
                ))}
              </select>
            </label>

            <fieldset className="bi-builder__metrics">
              <legend>{t('builder.metrics')}</legend>
              <div className="bi-builder__metric-list">
                {metrics.map((m) => (
                  <label key={m.key} className="bi-builder__metric">
                    <input
                      type="checkbox"
                      checked={selected.includes(m.key)}
                      onChange={(e) => {
                        setSelected((prev) =>
                          e.target.checked ? [...prev, m.key] : prev.filter((k) => k !== m.key),
                        );
                      }}
                    />
                    <span>
                      <strong>{m.name}</strong>
                      <small>
                        {m.domain} · {m.source}
                      </small>
                      <em>{m.description}</em>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

            {error ? <p className="bi-workspace__error">{error}</p> : null}

            <div className="bi-workspace__actions">
              <button type="submit" className="ih-btn ih-btn--primary" disabled={saving}>
                {saving ? t('states.saving') : t('builder.save')}
              </button>
            </div>
          </div>
        </form>
      ) : null}
    </BiWorkspaceShell>
  );
}
