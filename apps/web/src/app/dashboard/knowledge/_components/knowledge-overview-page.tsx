'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  fetchKnowledgeOverview,
  fetchKnowledgePipeline,
  type KnowledgeOverview,
  type KnowledgePipelineStatus,
} from '@/lib/api/knowledge';

import { KnowledgeHubShell } from './knowledge-hub-shell';
import { KnowledgeProviderBadge } from './knowledge-provider-badge';

function metricValue(
  metric: KnowledgeOverview['total_documents'],
  locale: string,
  asBytes = false,
): string {
  if (!metric.available || metric.value == null) return '—';
  if (asBytes) {
    const v = Number(metric.value);
    if (v < 1024) return `${v} B`;
    if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`;
    if (v < 1024 * 1024 * 1024) return `${(v / (1024 * 1024)).toFixed(1)} MB`;
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(v / (1024 * 1024 * 1024))} GB`;
  }
  return new Intl.NumberFormat(locale).format(Number(metric.value));
}

export function KnowledgeOverviewPage() {
  const t = useTranslations('knowledge');
  const locale = useLocale();
  const [overview, setOverview] = useState<KnowledgeOverview | null>(null);
  const [pipeline, setPipeline] = useState<KnowledgePipelineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [ov, pipe] = await Promise.all([
          fetchKnowledgeOverview(),
          fetchKnowledgePipeline().catch(() => null),
        ]);
        if (!cancelled) {
          setOverview(ov);
          setPipeline(pipe);
        }
      } catch {
        if (!cancelled) setError(t('loadError'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [t]);

  const widgets = overview
    ? [
        { key: 'total', label: t('widgets.total'), metric: overview.total_documents },
        { key: 'recent', label: t('widgets.recent'), metric: overview.recent_uploads },
        { key: 'review', label: t('widgets.awaitingReview'), metric: overview.awaiting_review },
        { key: 'expiring', label: t('widgets.expiring'), metric: overview.expiring_soon },
        { key: 'failed', label: t('widgets.failedJobs'), metric: overview.failed_jobs },
        { key: 'unlinked', label: t('widgets.unlinked'), metric: overview.unlinked },
        { key: 'dupes', label: t('widgets.duplicates'), metric: overview.duplicate_candidates },
        {
          key: 'storage',
          label: t('widgets.storage'),
          metric: overview.storage_used_bytes,
          bytes: true,
        },
        { key: 'collections', label: t('widgets.collections'), metric: overview.collections },
      ]
    : [];

  return (
    <KnowledgeHubShell>
      {loading && <p>{t('loading')}</p>}
      {error && <p className="leads-page__error" role="alert">{error}</p>}

      {overview && (
        <>
          <section className="documents-overview knowledge-hub__widgets" aria-label={t('widgets.title')}>
            {widgets.map((w) => {
              const href = (w.metric.drilldown || '/dashboard/knowledge/documents') as Route;
              return (
                <Link key={w.key} href={href} className="documents-overview__card">
                  <span className="documents-overview__label">{w.label}</span>
                  <strong className="documents-overview__value">
                    {metricValue(w.metric, locale, Boolean(w.bytes))}
                  </strong>
                </Link>
              );
            })}
          </section>

          <section className="knowledge-hub__providers" aria-label={t('providers.title')}>
            <h2 className="knowledge-hub__section-title">{t('providers.title')}</h2>
            <div className="knowledge-hub__provider-grid">
              <KnowledgeProviderBadge label={t('providers.indexing')} status={overview.indexing_status} />
              <KnowledgeProviderBadge label={t('providers.ocr')} status={overview.ocr_status} />
              <KnowledgeProviderBadge label={t('providers.ai')} status={overview.ai_status} />
              <KnowledgeProviderBadge label={t('providers.vector')} status={overview.vector_search_status} />
              <KnowledgeProviderBadge label={t('providers.malware')} status={overview.malware_scan_status} />
            </div>
            <p className="knowledge-hub__note">{t('providers.honestyNote')}</p>
          </section>

          {pipeline && (
            <section className="knowledge-hub__pipeline" aria-label={t('pipeline.title')}>
              <div className="knowledge-hub__section-head">
                <h2 className="knowledge-hub__section-title">{t('pipeline.title')}</h2>
                <Link href={'/dashboard/automation' as Route} className="button button--ghost">
                  {t('pipeline.automationLink')}
                </Link>
              </div>
              <div className="knowledge-hub__pipeline-stages">
                {pipeline.stages.map((stage) => (
                  <div
                    key={stage.stage}
                    className={`knowledge-hub__stage knowledge-hub__stage--${stage.status}`}
                  >
                    <span>{stage.label}</span>
                    <strong>{stage.count}</strong>
                  </div>
                ))}
              </div>
              {pipeline.note && <p className="knowledge-hub__note">{pipeline.note}</p>}
            </section>
          )}
        </>
      )}
    </KnowledgeHubShell>
  );
}
