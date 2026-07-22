'use client';

import Link from 'next/link';

import type { LoadState, MyWorkItem } from './types';

export function MyWorkPanel({
  title,
  hint,
  items,
  state,
  empty,
  unavailableTasks,
  unavailableMeetings,
  kindLabels,
  onRetry,
  retryLabel,
  errorMessage,
}: {
  title: string;
  hint: string;
  items: MyWorkItem[];
  state: LoadState;
  empty: string;
  unavailableTasks: string;
  unavailableMeetings: string;
  kindLabels?: Partial<Record<MyWorkItem['kind'], string>>;
  onRetry?: () => void;
  retryLabel: string;
  errorMessage: string;
}) {
  return (
    <section className="ecc-mywork" aria-label={title}>
      <div className="ecc-section-header">
        <h2 className="ecc-section-title">{title}</h2>
        <p className="ecc-section-hint">{hint}</p>
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
      {state === 'success' && (
        <>
          <p className="ecc-mywork__note">{unavailableTasks}</p>
          <p className="ecc-mywork__note">{unavailableMeetings}</p>
          {items.length === 0 ? (
            <p className="leads__state">{empty}</p>
          ) : (
            <ul className="ecc-mywork-list">
              {items.map((item) => (
                <li key={item.id}>
                  <Link href={item.href} className="ecc-mywork-item">
                    <span className="ecc-mywork-item__kind">
                      {kindLabels?.[item.kind] ?? item.kind}
                    </span>
                    <strong>{item.title}</strong>
                    <span>{item.meta}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}