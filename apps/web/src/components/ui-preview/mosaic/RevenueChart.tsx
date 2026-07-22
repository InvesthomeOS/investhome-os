'use client';

import { LineChart } from '@/components/design-system/charts';

import { REVENUE_SERIES, SALES_SERIES } from './demo-data';

/** Mosaic-style dual series using project DS SVG charts (no ApexCharts). */
export function RevenueSalesChart() {
  return (
    <div className="mosaic-chart-wrap" data-testid="mosaic-revenue-chart">
      <div className="mosaic-chart-legend">
        <span>
          <i className="mosaic-dot mosaic-dot--violet" /> Collections
        </span>
        <span>
          <i className="mosaic-dot mosaic-dot--sky" /> Sales closed
        </span>
      </div>
      <div className="mosaic-chart-grid">
        <LineChart
          data={[...REVENUE_SERIES]}
          ariaLabel="Monthly collections"
          locale="tr"
          format="compact"
          currency="TRY"
          height={180}
          title="Collections"
        />
        <LineChart
          data={[...SALES_SERIES]}
          ariaLabel="Monthly sales closed"
          locale="tr"
          format="compact"
          currency="TRY"
          height={180}
          title="Sales closed"
        />
      </div>
    </div>
  );
}
