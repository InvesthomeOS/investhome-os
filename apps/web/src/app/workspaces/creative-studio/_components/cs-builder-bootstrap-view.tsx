'use client';

/**
 * Shared loading / error shell for Document API bootstrap.
 * Keeps page header chrome visible; never renders an empty white workspace.
 */

import Link from 'next/link';
import type { Route } from 'next';
import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type { CsBuilderHydrationPhase } from './use-cs-builder-hydration';
import './cs-builder-bootstrap-view.css';

export type CsBuilderBootstrapViewProps = {
  testId: string;
  workspaceClassName: string;
  homeHref: string;
  title: string;
  studioLabel: string;
  phase: Exclude<CsBuilderHydrationPhase, 'ready'>;
  loadingLabel: string;
  errorTitle: string;
  errorMessage: string;
  retryLabel: string;
  onRetry: () => void;
};

export function CsBuilderBootstrapView({
  testId,
  workspaceClassName,
  homeHref,
  title,
  studioLabel,
  phase,
  loadingLabel,
  errorTitle,
  errorMessage,
  retryLabel,
  onRetry,
}: CsBuilderBootstrapViewProps) {
  return (
    <main className="dashboard" data-testid={testId}>
      <div
        className={`${workspaceClassName} cs-builder-bootstrap`}
        data-cs-bootstrap-phase={phase}
      >
        <header className="cs-builder-bootstrap__header cs-page-header">
          <div className="cs-builder-bootstrap__header-copy cs-page-header__copy">
            <Link href={homeHref as Route} className="cs-page-header__back">
              <IhIcon name="chevronLeft" size={12} />
              {studioLabel}
            </Link>
            <nav aria-label={studioLabel}>
              <ol className="cs-page-header__breadcrumb">
                <li>
                  <Link href={homeHref as Route}>{studioLabel}</Link>
                </li>
                <li className="cs-page-header__breadcrumb-sep" aria-hidden="true">
                  /
                </li>
                <li className="cs-page-header__breadcrumb-current" aria-current="page">
                  {title}
                </li>
              </ol>
            </nav>
            <h1>
              <IhIcon name="documents" size={20} />
              {title}
            </h1>
          </div>
        </header>

        <div className="cs-builder-bootstrap__body" role="status" aria-live="polite">
          {phase === 'loading' ? (
            <LoadingState label={loadingLabel} variant="skeleton" lines={5} />
          ) : (
            <ErrorState
              title={errorTitle}
              message={errorMessage}
              action={
                <Button variant="primary" size="sm" onClick={onRetry}>
                  {retryLabel}
                </Button>
              }
            />
          )}
        </div>
      </div>
    </main>
  );
}
