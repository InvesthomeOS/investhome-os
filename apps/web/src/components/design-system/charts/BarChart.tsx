'use client';

import { ChartContainer, type ChartContainerState } from '@investhome/ui';

import { DS_CHART_PRIMARY, formatChartValue, type ChartNumberFormat } from './format';

export interface BarChartPoint {
  label: string;
  value: number;
}

export interface BarChartProps {
  data: BarChartPoint[];
  ariaLabel: string;
  locale?: string;
  format?: ChartNumberFormat;
  currency?: string;
  state?: ChartContainerState;
  title?: string;
  emptyTitle?: string;
  loadingLabel?: string;
  className?: string;
  horizontal?: boolean;
}

export function BarChart({
  data,
  ariaLabel,
  locale = 'tr',
  format = 'number',
  currency = 'TRY',
  state,
  title,
  emptyTitle,
  loadingLabel,
  className,
  horizontal = true,
}: BarChartProps) {
  const resolvedState: ChartContainerState =
    state ?? (data.length === 0 ? 'empty' : 'ready');
  const max = Math.max(...data.map((d) => d.value), 1);
  const summary = data
    .map((d) => `${d.label}: ${formatChartValue(d.value, format, locale, currency)}`)
    .join('; ');

  return (
    <ChartContainer
      title={title}
      state={resolvedState}
      ariaLabel={ariaLabel}
      emptyTitle={emptyTitle}
      loadingLabel={loadingLabel}
      className={className}
    >
      {horizontal ? (
        <div className="ds-chart ds-chart--bar" role="img" aria-label={ariaLabel}>
          <p className="sr-only">{summary}</p>
          {data.map((d) => (
            <div key={d.label} className="inv-portfolio-hbar__row">
              <span className="inv-portfolio-hbar__label">{d.label}</span>
              <div className="inv-portfolio-hbar__track">
                <div
                  className="inv-portfolio-hbar__fill"
                  style={{
                    width: `${(d.value / max) * 100}%`,
                    backgroundColor: DS_CHART_PRIMARY,
                  }}
                />
              </div>
              <span className="inv-portfolio-hbar__value">
                {formatChartValue(d.value, format, locale, currency)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="ih-chart__bars" role="img" aria-label={ariaLabel}>
          <p className="sr-only">{summary}</p>
          {data.map((d) => (
            <div key={d.label} className="ih-chart__bar-col">
              <span className="ih-chart__bar-value">
                {formatChartValue(d.value, format, locale, currency)}
              </span>
              <div
                className="ih-chart__bar"
                style={{ height: `${(d.value / max) * 100}%`, background: DS_CHART_PRIMARY }}
              />
              <span className="ih-chart__bar-label">{d.label}</span>
            </div>
          ))}
        </div>
      )}
    </ChartContainer>
  );
}
