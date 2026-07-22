'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { CompanyHealthTone, LoadState } from './types';

export function CompanyHealthPanel({
  state,
  tone,
  title,
  statusLabel,
  summary,
  criticalCount,
  warningCount,
  atRiskProjects,
  overduePayments,
  labels,
  onRetry,
  retryLabel,
  href,
}: {
  state: LoadState;
  tone: CompanyHealthTone;
  title: string;
  statusLabel: string;
  summary: string;
  criticalCount: number;
  warningCount: number;
  atRiskProjects: number;
  overduePayments: boolean;
  labels: {
    critical: string;
    warning: string;
    atRiskProjects: string;
    overduePayments: string;
    noSignals: string;
  };
  onRetry?: () => void;
  retryLabel: string;
  href: Route;
}) {
  return (
    <section className="ecc-health" aria-label={title} data-tone={tone}>
      <div className="ecc-health__header">
        <div>
          <h2 className="ecc-health__title">{title}</h2>
          <p className="ecc-health__status">
            {state === 'success' ? (
              <span className={`ecc-health__badge ecc-health__badge--${tone}`}>{statusLabel}</span>
            ) : (
              <span className="ecc-health__badge ecc-health__badge--unknown" aria-hidden="true">
                …
              </span>
            )}
          </p>
        </div>
        <Link href={href} className="ecc-health__link">
          {summary}
        </Link>
      </div>

      {state === 'loading' && <div className="executive__skeleton" aria-hidden="true" />}
      {state === 'error' && (
        <div className="leads__state leads__state--error">
          <p>{summary}</p>
          {onRetry && (
            <button type="button" className="leads__button leads__button--secondary" onClick={onRetry}>
              {retryLabel}
            </button>
          )}
        </div>
      )}
      {state === 'success' && (
        <ul className="ecc-health__signals">
          <li>
            <strong>{criticalCount}</strong>
            <span>{labels.critical}</span>
          </li>
          <li>
            <strong>{warningCount}</strong>
            <span>{labels.warning}</span>
          </li>
          <li>
            <strong>{atRiskProjects}</strong>
            <span>{labels.atRiskProjects}</span>
          </li>
          <li>
            <strong>{overduePayments ? '!' : '—'}</strong>
            <span>{labels.overduePayments}</span>
          </li>
        </ul>
      )}
      {state === 'success' && criticalCount === 0 && warningCount === 0 && atRiskProjects === 0 && (
        <p className="ecc-health__empty">{labels.noSignals}</p>
      )}
    </section>
  );
}