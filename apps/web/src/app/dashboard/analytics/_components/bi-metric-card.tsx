'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import type { BiMetricValue } from '@/lib/analytics/bi-types';

function formatFreshness(
  iso: string | null | undefined,
  t: (key: string, values?: Record<string, number | string>) => string,
): string {
  if (!iso) return t('freshness.unknown');
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return t('freshness.unknown');
  const mins = Math.max(0, Math.round((Date.now() - then) / 60000));
  if (mins < 1) return t('freshness.justNow');
  if (mins < 60) return t('freshness.minutes', { count: mins });
  const hours = Math.round(mins / 60);
  return t('freshness.hours', { count: hours });
}

export function BiMetricCard({ metric }: { metric: BiMetricValue }) {
  const t = useTranslations('analytics');
  const unavailable = metric.state === 'unavailable' || metric.state === 'permission';
  const empty = metric.state === 'empty';
  const display = unavailable
    ? t('states.unavailable')
    : empty
      ? t('states.empty')
      : metric.value ?? t('states.empty');

  const change =
    metric.comparison?.change_available && metric.comparison.change_pct != null
      ? `${metric.comparison.change_pct > 0 ? '+' : ''}${metric.comparison.change_pct}%`
      : null;

  const body = (
    <article
      className={`bi-metric bi-metric--${metric.state}`}
      data-metric-key={metric.key}
      aria-label={`${metric.name}: ${display}`}
    >
      <header className="bi-metric__header">
        <h3 className="bi-metric__label">{metric.name}</h3>
        <span className="bi-metric__freshness">{formatFreshness(metric.freshness_at, t)}</span>
      </header>
      <p className="bi-metric__value">
        {display}
        {metric.unit && metric.state === 'ready' && metric.unit !== 'currency' ? (
          <span className="bi-metric__unit"> {metric.unit}</span>
        ) : null}
      </p>
      <div className="bi-metric__meta">
        {change ? (
          <span className={`bi-metric__delta${metric.comparison!.change_pct! < 0 ? ' bi-metric__delta--neg' : ''}`}>
            {change}
          </span>
        ) : (
          <span className="bi-metric__delta bi-metric__delta--na">{t('states.noComparison')}</span>
        )}
        {metric.date_from && metric.date_to ? (
          <span className="bi-metric__range">
            {metric.date_from} → {metric.date_to}
          </span>
        ) : null}
      </div>
      {metric.definition ? <p className="bi-metric__def">{metric.definition}</p> : null}
      {metric.source ? (
        <p className="bi-metric__source">
          {t('source')}: {metric.source}
        </p>
      ) : null}
      {metric.reason && metric.state !== 'ready' ? (
        <p className="bi-metric__reason">{metric.reason}</p>
      ) : null}
    </article>
  );

  if (metric.drilldown_path && metric.state === 'ready') {
    return (
      <Link href={metric.drilldown_path as Route} className="bi-metric__link">
        {body}
      </Link>
    );
  }
  return body;
}

export function BiMetricGrid({ metrics }: { metrics: BiMetricValue[] }) {
  return (
    <div className="bi-metric-grid">
      {metrics.map((m) => (
        <BiMetricCard key={m.key} metric={m} />
      ))}
    </div>
  );
}
