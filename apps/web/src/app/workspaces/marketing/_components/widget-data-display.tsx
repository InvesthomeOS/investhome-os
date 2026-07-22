'use client';

import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

import { resolveMarketingMetricLabel } from '@/lib/marketing/marketing-i18n';

import { MetricRow, TableWidget } from '../dashboard/_components/analytics-widgets';

type WidgetData = Record<string, unknown> | unknown[] | null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function formatValue(value: unknown, labels: { yes: string; no: string; metric: string }): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? labels.yes : labels.no;
  if (typeof value === 'number' || typeof value === 'string') return String(value);
  return '—';
}

function KeyValueList({
  data,
  format,
}: {
  data: Record<string, unknown>;
  format: (value: unknown) => string;
}) {
  const entries = Object.entries(data).filter(([, value]) => value !== null && value !== undefined);
  if (entries.length === 0) return null;

  return (
    <dl className="marketing-kv-list">
      {entries.map(([key, value]) => (
        <div key={key} className="marketing-kv-list__row">
          <dt className="marketing-kv-list__key">{key.replace(/_/g, ' ')}</dt>
          <dd className="marketing-kv-list__value">{format(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function MetricDataGrid({ metrics }: { metrics: Array<{ label: string; value: unknown; unit?: string | null; state?: string }> }) {
  return (
    <MetricRow
      metrics={metrics.map((metric) => ({
        label: metric.label,
        value: typeof metric.value === 'number' || typeof metric.value === 'string' ? metric.value : null,
        unit: metric.unit,
        state: metric.state ?? 'ready',
      }))}
    />
  );
}

export function WidgetDataDisplay({
  data,
  emptyLabel,
}: {
  data: WidgetData;
  emptyLabel?: string;
}) {
  const tCommon = useTranslations('marketing.common');
  const tAnalytics = useTranslations('marketing.analytics');
  const resolvedEmptyLabel = emptyLabel ?? tCommon('noData');
  const format = (value: unknown) =>
    formatValue(value, { yes: tCommon('yes'), no: tCommon('no'), metric: tCommon('metric') });

  if (data === null || data === undefined) {
    return <EmptyState title={resolvedEmptyLabel} description={resolvedEmptyLabel} />;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <EmptyState title={resolvedEmptyLabel} description={resolvedEmptyLabel} />;
    }

    if (data.every(isRecord)) {
      const columns = Array.from(
        new Set(data.flatMap((row) => Object.keys(row).filter((key) => typeof row[key] !== 'object'))),
      ).slice(0, 6);

      if (columns.length > 0) {
        return <TableWidget rows={data} columns={columns} />;
      }
    }

    return (
      <ul className="marketing-data-list">
        {data.map((item, index) => (
          <li key={index} className="marketing-data-list__item">
            {isRecord(item) ? <KeyValueList data={item} format={format} /> : format(item)}
          </li>
        ))}
      </ul>
    );
  }

  if (isRecord(data)) {
    if (Array.isArray(data.metrics)) {
      const metrics = data.metrics
        .filter(isRecord)
        .map((metric) => ({
          label: resolveMarketingMetricLabel(
            tAnalytics,
            typeof metric.key === 'string' ? metric.key : null,
            typeof metric.label === 'string' ? metric.label : null,
          ) || tCommon('metric'),
          value: metric.value,
          unit: typeof metric.unit === 'string' ? metric.unit : null,
          state: typeof metric.state === 'string' ? metric.state : 'ready',
        }));

      if (metrics.length > 0) {
        return <MetricDataGrid metrics={metrics} />;
      }
    }

    if (Array.isArray(data.items) && data.items.every(isRecord)) {
      const rows = data.items as Record<string, unknown>[];
      const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row)))).slice(0, 6);
      if (columns.length > 0) {
        return <TableWidget rows={rows} columns={columns} />;
      }
    }

    return <KeyValueList data={data} format={format} />;
  }

  return <span className="marketing-data-list__item">{format(data)}</span>;
}

export function ScoreSummary({ scores }: { scores: Record<string, unknown> }) {
  const entries = Object.entries(scores).filter(([, value]) => value !== null && value !== undefined);
  if (entries.length === 0) return null;

  return (
    <MetricRow
      metrics={entries.map(([key, value]) => ({
        label: key.replace(/_/g, ' '),
        value: typeof value === 'number' || typeof value === 'string' ? value : null,
        state: 'ready',
      }))}
    />
  );
}

export function SegmentRulesList({
  ruleGroups,
  emptyLabel,
}: {
  ruleGroups: unknown[];
  emptyLabel: string;
}) {
  if (!ruleGroups.length) {
    return <EmptyState title={emptyLabel} description={emptyLabel} />;
  }

  return (
    <div className="marketing-rules-list">
      {ruleGroups.map((group, groupIndex) => {
        if (!isRecord(group)) return null;
        const rules = Array.isArray(group.rules) ? group.rules.filter(isRecord) : [];

        return (
          <section key={groupIndex} className="marketing-rules-list__group">
            <h3 className="marketing-rules-list__title">
              {typeof group.name === 'string' ? group.name : `Group ${groupIndex + 1}`}
            </h3>
            {rules.length === 0 ? (
              <p className="marketing-rules-list__empty">{emptyLabel}</p>
            ) : (
              <TableWidget
                rows={rules}
                columns={['field', 'operator', 'value', 'logic'].filter((col) =>
                  rules.some((rule) => col in rule),
                )}
              />
            )}
          </section>
        );
      })}
    </div>
  );
}
