'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';

import type { AlertItemView, LoadState } from './types';

type SeverityFilter = 'all' | 'critical' | 'warning' | 'information';

export function AlertCenter({
  title,
  items,
  state,
  empty,
  filterLabels,
  severityLabels,
  onRetry,
  retryLabel,
  errorMessage,
}: {
  title: string;
  items: AlertItemView[];
  state: LoadState;
  empty: string;
  filterLabels: Record<SeverityFilter, string>;
  severityLabels?: Partial<Record<'critical' | 'warning' | 'information', string>>;
  onRetry?: () => void;
  retryLabel: string;
  errorMessage: string;
}) {
  const [filter, setFilter] = useState<SeverityFilter>('all');
  const filtered = useMemo(
    () => (filter === 'all' ? items : items.filter((item) => item.severity === filter)),
    [filter, items],
  );

  return (
    <section className="ecc-alerts" aria-label={title}>
      <div className="ecc-section-header ecc-section-header--row">
        <h2 className="ecc-section-title">{title}</h2>
        <div className="ecc-alert-filters" role="tablist" aria-label={title}>
          {(['all', 'critical', 'warning', 'information'] as const).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={filter === key}
              className={`ecc-alert-filter${filter === key ? ' ecc-alert-filter--active' : ''}`}
              onClick={() => setFilter(key)}
            >
              {filterLabels[key]}
            </button>
          ))}
        </div>
      </div>
      {state === 'loading' && <div className="executive__skeleton" aria-hidden="true" />}
      {state === 'error' && (
        <div className="leads__state leads__state--error">
          <p>{errorMessage}</p>
          {onRetry && (
            <button type="button" className="leads__button leads__button--secondary" onClick={onRetry}>
              {retryLabel}
            </button>
          )}
        </div>
      )}
      {state === 'success' && filtered.length === 0 && <p className="leads__state">{empty}</p>}
      {state === 'success' && filtered.length > 0 && (
        <ul className="ecc-alert-list">
          {filtered.map((item) => {
            const content = (
              <>
                <span className={`ecc-alert-severity ecc-alert-severity--${item.severity}`}>
                  {severityLabels?.[item.severity] ?? item.severity}
                </span>
                <span className="ecc-alert-source">{item.source}</span>
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </>
            );
            return (
              <li key={item.id} className={`ecc-alert-item ecc-alert-item--${item.severity}`}>
                {item.href ? (
                  <Link href={item.href} className="ecc-alert-item__link">
                    {content}
                  </Link>
                ) : (
                  <div className="ecc-alert-item__link">{content}</div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}