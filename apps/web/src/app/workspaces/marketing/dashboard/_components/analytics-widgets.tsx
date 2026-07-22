'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { Button, LoadingState } from '@investhome/ui';

import { resolveMarketingMetricLabel } from '@/lib/marketing/marketing-i18n';

export type WidgetState = 'loading' | 'error' | 'permission' | 'unknown' | 'empty' | 'ready';

type WidgetShellProps = {
  title: string;
  subtitle?: string;
  state: WidgetState;
  children?: ReactNode;
  onRefresh?: () => void;
  onExport?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  className?: string;
};

export function WidgetShell({
  title,
  subtitle,
  state,
  children,
  onRefresh,
  onExport,
  collapsed,
  onToggleCollapse,
  className = '',
}: WidgetShellProps) {
  const t = useTranslations('marketing.analytics.widgetStates');

  return (
    <section className={`mkt-widget ${className}`}>
      <header className="mkt-widget__header">
        <div>
          <h3 className="mkt-widget__title">{title}</h3>
          {subtitle ? <p className="mkt-widget__subtitle">{subtitle}</p> : null}
        </div>
        <div className="mkt-widget__actions">
          {onToggleCollapse ? (
            <button type="button" className="mkt-widget__action-btn" onClick={onToggleCollapse} aria-expanded={!collapsed}>
              {collapsed ? '▼' : '▲'}
            </button>
          ) : null}
          {onRefresh ? (
            <button type="button" className="mkt-widget__action-btn" onClick={onRefresh}>
              ↻
            </button>
          ) : null}
          {onExport ? (
            <button type="button" className="mkt-widget__action-btn" onClick={onExport}>
              ⤓
            </button>
          ) : null}
        </div>
      </header>
      {!collapsed ? (
        <div className="mkt-widget__body">
          {state === 'loading' ? <LoadingState label={t('loading')} /> : null}
          {state === 'error' ? <p className="mkt-widget__state mkt-widget__state--error">{t('error')}</p> : null}
          {state === 'permission' ? <p className="mkt-widget__state">{t('permission')}</p> : null}
          {state === 'unknown' ? <p className="mkt-widget__state">{t('unknown')}</p> : null}
          {state === 'empty' ? <p className="mkt-widget__state">{t('empty')}</p> : null}
          {state === 'ready' ? children : null}
        </div>
      ) : null}
    </section>
  );
}

type MetricCardProps = {
  label: string;
  value: string | number | null | undefined;
  unit?: string | null;
  state: string;
  evidence?: Record<string, unknown> | null;
};

export function MetricCard({ label, value, unit, state, evidence }: MetricCardProps) {
  const t = useTranslations('marketing.analytics');
  const display =
    state === 'unknown' || state === 'unavailable' || state === 'not_connected'
      ? t('unknown')
      : value ?? t('empty');

  return (
    <div className={`mkt-metric mkt-metric--${state}`}>
      <span className="mkt-metric__label">{label}</span>
      <span className="mkt-metric__value">
        {display}
        {unit && state === 'ready' ? <span className="mkt-metric__unit">{unit}</span> : null}
      </span>
      {evidence?.reason ? (
        <span className="mkt-metric__hint">{String(evidence.reason)}</span>
      ) : null}
    </div>
  );
}

export function MetricRow({ metrics }: { metrics: MetricCardProps[] }) {
  return (
    <div className="mkt-metric-row">
      {metrics.map((m) => (
        <MetricCard key={m.label} {...m} />
      ))}
    </div>
  );
}

export function FunnelWidget({ stages }: { stages: Array<{ key: string; label: string; count?: number | null; state: string; conversion_percent?: number | null; drop_off_percent?: number | null }> }) {
  const t = useTranslations('marketing.analytics');

  return (
    <div className="mkt-funnel">
      {stages.map((stage, index) => (
        <div key={stage.key} className={`mkt-funnel__stage mkt-funnel__stage--${stage.state}`}>
          <div className="mkt-funnel__stage-header">
            <span className="mkt-funnel__stage-num">{index + 1}</span>
            <span className="mkt-funnel__stage-label">
              {resolveMarketingMetricLabel(t, stage.key, stage.label)}
            </span>
          </div>
          <div className="mkt-funnel__stage-value">
            {stage.state === 'unknown' || stage.count === null ? t('unknown') : stage.count}
          </div>
          {stage.conversion_percent != null ? (
            <div className="mkt-funnel__stage-meta">
              {stage.conversion_percent}% · −{stage.drop_off_percent}%
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function StatusGrid({ items }: { items: Array<{ key: string; label: string; status: string; summary?: string | null }> }) {
  const t = useTranslations('marketing.analytics');

  return (
    <div className="mkt-status-grid">
      {items.map((item) => (
        <div key={item.key} className={`mkt-status-grid__item mkt-status-grid__item--${item.status}`}>
          <span className="mkt-status-grid__label">
            {resolveMarketingMetricLabel(t, item.key, item.label)}
          </span>
          <span className="mkt-status-grid__status">{item.status}</span>
          {item.summary ? <span className="mkt-status-grid__summary">{item.summary}</span> : null}
        </div>
      ))}
    </div>
  );
}

export function AlertPanel({ alerts }: { alerts: Array<{ id: string; title: string; message?: string | null; severity: string }> }) {
  return (
    <ul className="mkt-alert-panel">
      {alerts.map((alert) => (
        <li key={alert.id} className={`mkt-alert-panel__item mkt-alert-panel__item--${alert.severity}`}>
          <strong>{alert.title}</strong>
          {alert.message ? <p>{alert.message}</p> : null}
        </li>
      ))}
    </ul>
  );
}

export function RecommendationPanel({ items }: { items: Array<{ id: string; title: string; rationale?: string | null; description?: string | null }> }) {
  return (
    <ul className="mkt-recommendation-panel">
      {items.map((item) => (
        <li key={item.id} className="mkt-recommendation-panel__item">
          <strong>{item.title}</strong>
          <p>{item.rationale ?? item.description}</p>
        </li>
      ))}
    </ul>
  );
}

export function TableWidget({
  rows,
  columns,
  columnLabels,
}: {
  rows: Record<string, unknown>[];
  columns: string[];
  columnLabels?: Record<string, string>;
}) {
  if (rows.length === 0) return null;
  return (
    <div className="mkt-table-widget">
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{columnLabels?.[col] ?? col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col}>{String(row[col] ?? '—')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TimeFilterBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (preset: string) => void;
}) {
  const t = useTranslations('marketing.analytics.timeFilters');
  const presets = ['today', 'yesterday', 'last_7_days', 'last_30_days', 'last_90_days', 'this_month', 'quarter', 'year'] as const;

  return (
    <div className="mkt-time-filter">
      {presets.map((preset) => (
        <Button
          key={preset}
          type="button"
          variant={value === preset ? 'primary' : 'secondary'}
          onClick={() => onChange(preset)}
        >
          {t(preset)}
        </Button>
      ))}
    </div>
  );
}
