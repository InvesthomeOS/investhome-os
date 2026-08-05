'use client';

import { useEffect, useMemo, useState, useTransition } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { EmptyState, LoadingState } from '@investhome/ui';

import { BiAreaPlaceholder, BiFunnel, DonutChart, HorizontalBarChart } from '@/components/analytics/bi-charts';
import { useAiCopilot } from '@/lib/ai/ai-copilot-context';
import { fetchBiDomain, biExportUrl } from '@/lib/analytics/bi-api';
import { useBiFilters } from '@/lib/analytics/bi-filters';
import { canExportAnalytics, canViewAnalytics } from '@/lib/analytics/bi-permissions';
import type { BiDomain, BiDomainResponse } from '@/lib/analytics/bi-types';
import { getApiBaseUrl } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';

import { BiMetricGrid } from './bi-metric-card';
import { BiWorkspaceShell } from './bi-workspace-shell';

function useDebouncedFilters(filters: ReturnType<typeof useBiFilters>['filters'], delay = 300) {
  const [debounced, setDebounced] = useState(filters);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(filters), delay);
    return () => window.clearTimeout(id);
  }, [filters, delay]);
  return debounced;
}

export function BiDomainPage({
  domain,
  titleKey,
  subtitleKey,
}: {
  domain: BiDomain;
  titleKey: string;
  subtitleKey: string;
}) {
  const t = useTranslations('analytics');
  const { user } = useAuth();
  const { openCopilot } = useAiCopilot();
  const { filters } = useBiFilters();
  const debounced = useDebouncedFilters(filters);
  const [data, setData] = useState<BiDomainResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [, startTransition] = useTransition();

  const filterKey = useMemo(() => JSON.stringify(debounced), [debounced]);

  useEffect(() => {
    if (!canViewAnalytics(user)) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    void fetchBiDomain(domain, debounced)
      .then((res) => {
        if (!cancelled) {
          startTransition(() => {
            setData(res);
            setLoading(false);
          });
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'error');
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [domain, filterKey, user, debounced]);

  if (!canViewAnalytics(user)) {
    return (
      <BiWorkspaceShell title={t(titleKey as 'pages.executive.title')} subtitle={t(subtitleKey as 'pages.executive.subtitle')}>
        <div className="ih-panel">
          <div className="ih-panel__body">
            <p className="bi-workspace__empty">{t('accessDenied')}</p>
          </div>
        </div>
      </BiWorkspaceShell>
    );
  }

  const canExport = canExportAnalytics(user);

  const actions = (
    <div className="bi-workspace__actions">
      <button
        type="button"
        className="ih-btn ih-btn--secondary"
        onClick={() => {
          const metricKeys =
            data?.sections.flatMap((s) => s.metrics.map((m) => m.key)).join(', ') ?? '';
          openCopilot(
            t('ai.prompt', {
              domain,
              filters: JSON.stringify(debounced),
              metrics: metricKeys,
            }),
          );
        }}
      >
        {t('ai.ask')}
      </button>
      {canExport ? (
        <button
          type="button"
          className="ih-btn ih-btn--secondary"
          onClick={async () => {
            const path = biExportUrl('csv', debounced, domain);
            const res = await fetch(`${getApiBaseUrl()}${path}`, { credentials: 'include' });
            const text = await res.text();
            const blob = new Blob([text], { type: 'text/csv' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `bi_${domain}.csv`;
            a.click();
            URL.revokeObjectURL(a.href);
          }}
        >
          {t('export.csv')}
        </button>
      ) : null}
      <button type="button" className="ih-btn ih-btn--ghost" onClick={() => window.print()}>
        {t('export.print')}
      </button>
    </div>
  );

  return (
    <BiWorkspaceShell
      title={t(titleKey as 'pages.executive.title')}
      subtitle={t(subtitleKey as 'pages.executive.subtitle')}
      actions={actions}
    >
      <p className="bi-workspace__ai-label">{t('ai.disclaimer')}</p>

      {loading ? <LoadingState label={t('states.loading')} lines={6} /> : null}
      {error ? (
        <div className="ih-panel">
          <div className="ih-panel__body">
            <p className="bi-workspace__error">{t('states.error')}</p>
          </div>
        </div>
      ) : null}

      {!loading && !error && data && data.sections.length === 0 ? (
        <EmptyState
          title={t('states.empty')}
          description={t('states.unavailable')}
          className="bi-workspace__empty-panel"
        />
      ) : null}

      {!loading && !error && data && data.sections.length > 0
        ? data.sections.map((section) => (
            <section key={section.key} className="bi-section ih-panel">
              <div className="ih-panel__body">
                <h2 className="bi-section__title">{section.title}</h2>
                {section.notes?.length ? (
                  <ul className="bi-section__notes">
                    {section.notes.map((note) => (
                      <li key={note}>{note}</li>
                    ))}
                  </ul>
                ) : null}
                {section.metrics?.length ? <BiMetricGrid metrics={section.metrics} /> : null}
                {section.series?.length ? (
                  <div className="bi-section__charts">
                    <BiAreaPlaceholder
                      points={section.series
                        .filter((s) => s.value != null)
                        .map((s) => ({ label: s.label, value: Number(s.value) }))}
                      ariaLabel={`${section.title} trend`}
                    />
                    <HorizontalBarChart
                      data={section.series
                        .filter((s) => s.value != null)
                        .slice(0, 8)
                        .map((s) => ({ label: s.label, value: Number(s.value) }))}
                      ariaLabel={`${section.title} bars`}
                    />
                    {domain === 'sales' || domain === 'marketing' ? (
                      <BiFunnel
                        stages={section.series.map((s) => ({
                          label: s.label,
                          value: s.value,
                          state: s.state,
                        }))}
                      />
                    ) : null}
                  </div>
                ) : null}
                {section.attribution_breakdown ? (
                  <DonutChart
                    data={Object.entries(section.attribution_breakdown).map(([label, value]) => ({
                      label,
                      value,
                    }))}
                    ariaLabel={t('attribution.aria')}
                  />
                ) : domain === 'marketing' ? (
                  <p className="bi-workspace__empty">{t('attribution.unavailable')}</p>
                ) : null}
                {section.rows?.length ? (
                  <div className="bi-table-wrap">
                    <table className="bi-table">
                      <thead>
                        <tr>
                          {Object.keys(section.rows[0]!).map((col) => (
                            <th key={col}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {section.rows.map((row, idx) => (
                          <tr key={idx}>
                            {Object.entries(row).map(([col, val]) => (
                              <td key={col}>
                                {col === 'drilldown' && typeof val === 'string' ? (
                                  <Link href={val as Route}>{t('drilldown')}</Link>
                                ) : (
                                  String(val ?? '—')
                                )}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            </section>
          ))
        : null}

      {data?.missing_sources?.length ? (
        <aside className="bi-missing ih-panel">
          <div className="ih-panel__body">
            <h2 className="bi-section__title">{t('missingSources')}</h2>
            <ul>
              {data.missing_sources.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
            <Link href={'/dashboard/analytics/data-quality' as Route}>{t('nav.dataQuality')}</Link>
          </div>
        </aside>
      ) : null}
    </BiWorkspaceShell>
  );
}
