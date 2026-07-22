'use client';

import Link from 'next/link';

import type { LoadState, PriorityItemView } from './types';

export function TodaysPriorities({
  id,
  title,
  hint,
  items,
  state,
  emptyTitle,
  emptyBody,
  severityLabels,
  onRetry,
  retryLabel,
  errorMessage,
}: {
  id?: string;
  title: string;
  hint: string;
  items: PriorityItemView[];
  state: LoadState;
  emptyTitle: string;
  emptyBody: string;
  severityLabels?: Partial<Record<'critical' | 'warning' | 'information', string>>;
  onRetry?: () => void;
  retryLabel: string;
  errorMessage: string;
}) {
  return (
    <section id={id} className="ecc-priorities" aria-label={title}>
      <div className="ecc-section-header">
        <div>
          <h2 className="ecc-section-title">{title}</h2>
          <p className="ecc-section-hint">{hint}</p>
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
      {state === 'success' && items.length === 0 && (
        <div className="ecc-empty">
          <strong>{emptyTitle}</strong>
          <p>{emptyBody}</p>
        </div>
      )}
      {state === 'success' && items.length > 0 && (
        <ul className="ecc-priority-list">
          {items.map((item) => (
            <li key={item.id}>
              <Link
                href={item.href}
                className={`ecc-priority-item ecc-priority-item--${item.severity}`}
              >
                <span className="ecc-priority-item__severity">
                  {severityLabels?.[item.severity] ?? item.severity}
                </span>
                <span className="ecc-priority-item__category">{item.category}</span>
                <strong className="ecc-priority-item__title">{item.title}</strong>
                <p className="ecc-priority-item__desc">{item.description}</p>
                {item.dueLabel && <span className="ecc-priority-item__due">{item.dueLabel}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
