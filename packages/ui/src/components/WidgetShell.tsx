import type { ReactNode } from 'react';

import { EmptyState } from './EmptyState.js';
import { ErrorState } from './ErrorState.js';
import { SkeletonState } from './SkeletonState.js';
import { StatusBadge, type StatusBadgeTone } from './StatusBadge.js';

export type WidgetSpan = 3 | 4 | 6 | 8 | 12;
export type WidgetShellState = 'ready' | 'loading' | 'empty' | 'error';

export interface WidgetShellProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  status?: { label: string; tone?: StatusBadgeTone };
  action?: ReactNode;
  overflow?: ReactNode;
  state?: WidgetShellState;
  loadingLabel?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  errorTitle?: string;
  errorMessage?: string;
  errorAction?: ReactNode;
  footer?: ReactNode;
  span?: WidgetSpan;
  children?: ReactNode;
  className?: string;
  /** Accessible name override for the widget region */
  ariaLabel?: string;
}

export function WidgetShell({
  title,
  description,
  icon,
  status,
  action,
  overflow,
  state = 'ready',
  loadingLabel = 'Loading…',
  emptyTitle = 'No data',
  emptyDescription,
  emptyAction,
  errorTitle,
  errorMessage = 'Something went wrong',
  errorAction,
  footer,
  span,
  children,
  className,
  ariaLabel,
}: WidgetShellProps) {
  const classes = [
    'ds-widget-shell',
    span ? `ds-widget-shell--span-${span}` : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  let body: ReactNode = children;
  if (state === 'loading') {
    body = <SkeletonState label={loadingLabel} lines={3} />;
  } else if (state === 'empty') {
    body = (
      <EmptyState title={emptyTitle} description={emptyDescription} action={emptyAction} />
    );
  } else if (state === 'error') {
    body = (
      <ErrorState title={errorTitle} message={errorMessage} action={errorAction} compact />
    );
  }

  return (
    <section
      className={classes}
      aria-label={ariaLabel ?? title}
      aria-busy={state === 'loading' || undefined}
    >
      <header className="ds-widget-shell__header">
        <div className="ds-widget-shell__title-block">
          {icon ? <span className="ds-widget-shell__icon">{icon}</span> : null}
          <div className="ds-widget-shell__titles">
            <h3 className="ds-widget-shell__title">{title}</h3>
            {description ? <p className="ds-widget-shell__description">{description}</p> : null}
          </div>
        </div>
        <div className="ds-widget-shell__actions">
          {status ? <StatusBadge tone={status.tone}>{status.label}</StatusBadge> : null}
          {action}
          {overflow}
        </div>
      </header>
      <div className="ds-widget-shell__body">{body}</div>
      {footer ? <footer className="ds-widget-shell__footer">{footer}</footer> : null}
    </section>
  );
}
