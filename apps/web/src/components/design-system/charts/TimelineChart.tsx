'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { formatChartDate } from './format';

export interface TimelineEvent {
  id: string;
  label: string;
  at: string;
  description?: string;
}

export interface TimelineChartProps {
  events: TimelineEvent[];
  ariaLabel: string;
  locale?: string;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
}

export function TimelineChart({
  events,
  ariaLabel,
  locale = 'tr',
  state,
  title,
  emptyTitle,
  loadingLabel,
  className,
}: TimelineChartProps) {
  const resolvedState: ChartContainerState =
    state ?? (events.length === 0 ? 'empty' : 'ready');

  return (
    <ChartContainer
      title={title}
      state={resolvedState}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
    >
      <ol className="ds-chart--timeline" aria-label={ariaLabel}>
        {events.map((event) => (
          <li key={event.id} className="ds-chart--timeline__item">
            <span className="ds-chart--timeline__dot" aria-hidden="true" />
            <div>
              <p className="ds-type-label">{event.label}</p>
              <p className="ds-type-caption">{formatChartDate(event.at, locale)}</p>
              {event.description ? (
                <p className="ds-type-body-small">{event.description}</p>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </ChartContainer>
  );
}
