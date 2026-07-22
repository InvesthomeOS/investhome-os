import type { ReactNode } from 'react';

import { EmptyState } from './EmptyState.js';
import { ErrorState } from './ErrorState.js';
import { SkeletonState } from './SkeletonState.js';

export type ChartContainerState = 'ready' | 'loading' | 'empty' | 'error';

export interface ChartLegendItem {
  label: string;
  color: string;
}

export interface ChartContainerProps {
  title?: string;
  description?: string;
  legend?: ChartLegendItem[];
  state?: ChartContainerState;
  loadingLabel?: string;
  emptyTitle?: string;
  emptyDescription?: string;
  errorMessage?: string;
  children?: ReactNode;
  className?: string;
  ariaLabel?: string;
}

export function ChartContainer({
  title,
  description,
  legend,
  state = 'ready',
  loadingLabel = 'Loading…',
  emptyTitle = 'No chart data',
  emptyDescription,
  errorMessage = 'Unable to render chart',
  children,
  className,
  ariaLabel,
}: ChartContainerProps) {
  let plot: ReactNode = children;
  if (state === 'loading') {
    plot = <SkeletonState label={loadingLabel} lines={2} />;
  } else if (state === 'empty') {
    plot = <EmptyState title={emptyTitle} description={emptyDescription} />;
  } else if (state === 'error') {
    plot = <ErrorState message={errorMessage} compact />;
  }

  return (
    <div
      className={`ds-chart-container${className ? ` ${className}` : ''}`}
      role="group"
      aria-label={ariaLabel ?? title}
    >
      {(title || description || (legend && legend.length > 0)) && (
        <div className="ds-chart-container__header">
          <div>
            {title ? <h4 className="ds-type-card-title">{title}</h4> : null}
            {description ? <p className="ds-type-caption">{description}</p> : null}
          </div>
          {legend && legend.length > 0 ? (
            <ul className="ds-chart-container__legend">
              {legend.map((item) => (
                <li key={item.label} className="ds-chart-container__legend-item">
                  <span
                    className="ds-chart-container__swatch"
                    style={{ background: item.color }}
                    aria-hidden="true"
                  />
                  {item.label}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      )}
      <div className="ds-chart-container__plot">{plot}</div>
    </div>
  );
}
