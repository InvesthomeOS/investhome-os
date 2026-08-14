'use client';

import type { ReactNode } from 'react';

export function StatusBadge({ status, children }: { status: string; children?: ReactNode }) {
  const tone =
    status === 'configured' ||
    status === 'connected' ||
    status === 'healthy' ||
    status === 'active' ||
    status === 'ready' ||
    status === 'available' ||
    status === 'enabled' ||
    status === 'allow' ||
    status === 'allowed' ||
    status === 'pilot' ||
    status === 'live' ||
    status === 'editable' ||
    status === 'ok'
      ? 'ok'
      : status === 'missing' ||
          status === 'unavailable' ||
          status === 'not_configured' ||
          status === 'not_connected' ||
          status === 'planned' ||
          status === 'partial' ||
          status === 'demo' ||
          status === 'not_required' ||
          status === 'not required'
        ? 'warn'
        : status === 'invalid' ||
            status === 'degraded' ||
            status === 'expired' ||
            status === 'blocked' ||
            status === 'deny' ||
            status === 'denied' ||
            status === 'kill_switch' ||
            status === 'forbidden' ||
            status === 'immutable' ||
            status === 'dead'
          ? 'bad'
          : status === 'disabled' || status === 'inactive'
            ? 'muted'
            : 'neutral';
  return <span className={`sec-badge sec-badge--${tone}`}>{children ?? status.replace(/_/g, ' ')}</span>;
}

export function SecSection({
  title,
  description,
  children,
  actions,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <section className="sec-section">
      <div className="sec-section__head">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div className="sec-section__actions">{actions}</div> : null}
      </div>
      {children}
    </section>
  );
}

export function KpiGrid({
  items,
}: {
  items: Array<{ key: string; label: string; value: number | string | null; available: boolean; note?: string | null }>;
}) {
  return (
    <div className="sec-kpi-grid" data-sec-kpis>
      {items.map((kpi) => (
        <article key={kpi.key} className={`sec-kpi${!kpi.available ? ' sec-kpi--unavailable' : ''}`}>
          <p className="sec-kpi__label">{kpi.label}</p>
          <p className="sec-kpi__value">{kpi.available ? (kpi.value ?? '—') : 'Unavailable'}</p>
          {kpi.note ? <p className="sec-kpi__note">{kpi.note}</p> : null}
        </article>
      ))}
    </div>
  );
}

export function ProviderTable({
  items,
  emptyLabel,
}: {
  items: Array<{
    provider_id: string;
    label: string;
    status: string;
    message?: string | null;
    env_keys?: string[];
  }>;
  emptyLabel: string;
}) {
  if (!items.length) {
    return <p className="sec-empty">{emptyLabel}</p>;
  }
  return (
    <div className="sec-table-wrap">
      <table className="sec-table">
        <thead>
          <tr>
            <th>Provider</th>
            <th>Status</th>
            <th>Notes</th>
            <th>Env keys</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.provider_id}>
              <td>{item.label}</td>
              <td>
                <StatusBadge status={item.status} />
              </td>
              <td>{item.message ?? '—'}</td>
              <td>
                <code className="sec-code">{(item.env_keys ?? []).join(', ') || '—'}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
