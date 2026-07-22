import type { ReactNode } from 'react';

import { Card, type CardProps } from './Card.js';

export type V2CardProps = CardProps;

/**
 * Explicit V2 card surface — same Card API with `ds-v2-card` for opt-in chrome.
 * Prefer under `[data-ds-version="v2"]` so tokens map to white/navy/blue/gray.
 */
export function V2Card({ className, ...props }: V2CardProps) {
  const classes = ['ds-v2-card', className].filter(Boolean).join(' ');
  return <Card className={classes} {...props} />;
}

export type DashboardPanelProps = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  id?: string;
};

/** Dashboard section panel — V2 card separation (border + premium shadow). */
export function DashboardPanel({
  title,
  description,
  actions,
  children,
  className,
  id,
}: DashboardPanelProps) {
  return (
    <section
      id={id}
      className={['ds-dashboard-panel', className].filter(Boolean).join(' ')}
      aria-label={title}
    >
      {(title || actions || description) && (
        <header className="ds-dashboard-panel__header">
          <div>
            {title ? <h3 className="ds-dashboard-panel__title">{title}</h3> : null}
            {description ? <p className="ds-dashboard-panel__description">{description}</p> : null}
          </div>
          {actions ? <div className="ds-action-button-group">{actions}</div> : null}
        </header>
      )}
      <div className="ds-dashboard-panel__body">{children}</div>
    </section>
  );
}

export type ActionButtonGroupProps = {
  children?: ReactNode;
  className?: string;
  /** Accessible name for the control group */
  ariaLabel?: string;
};

export function ActionButtonGroup({ children, className, ariaLabel }: ActionButtonGroupProps) {
  return (
    <div
      className={['ds-action-button-group', className].filter(Boolean).join(' ')}
      role="group"
      aria-label={ariaLabel}
    >
      {children}
    </div>
  );
}

export type ProgressIndicatorProps = {
  value: number;
  label?: string;
  valueLabel?: string;
  className?: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
};

/** Labeled progress bar — not color-only (valueLabel / aria). */
export function ProgressIndicator({
  value,
  label,
  valueLabel,
  className,
  tone = 'default',
}: ProgressIndicatorProps) {
  const clamped = Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const classes = [
    'ds-progress-indicator',
    tone !== 'default' ? `ds-progress-indicator--${tone}` : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={classes} role="group" aria-label={label}>
      {(label || valueLabel) && (
        <div className="ds-progress-indicator__meta">
          {label ? <span>{label}</span> : <span />}
          {valueLabel ? <span>{valueLabel}</span> : <span>{Math.round(clamped)}%</span>}
        </div>
      )}
      <div
        className="ds-progress-indicator__track"
        role="progressbar"
        aria-valuenow={Math.round(clamped)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label ?? valueLabel ?? 'Progress'}
      >
        <i
          className="ds-progress-indicator__fill"
          style={{ width: `${clamped}%` }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}
