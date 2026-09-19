export interface LineChartPoint {
  label: string;
  value: number;
}

export interface LineChartProps {
  data: LineChartPoint[];
  ariaLabel: string;
  locale?: string;
  height?: number;
  title?: string;
  className?: string;
  format?: string;
}

export function LineChart({ data, ariaLabel, title, className }: LineChartProps) {
  return (
    <div role="img" aria-label={ariaLabel} className={className} data-points={data.length}>
      {title}
    </div>
  );
}

export interface AreaChartPoint {
  label: string;
  value: number;
}

export interface AreaChartProps {
  data: AreaChartPoint[];
  ariaLabel: string;
  locale?: string;
  height?: number;
  title?: string;
  className?: string;
  format?: string;
}

export function AreaChart({ data, ariaLabel, title, className }: AreaChartProps) {
  return (
    <div role="img" aria-label={ariaLabel} className={className} data-points={data.length}>
      {title}
    </div>
  );
}

export interface SparklineProps {
  data?: number[];
  values?: number[];
  ariaLabel?: string;
  className?: string;
}

export function Sparkline({ data, values, ariaLabel, className }: SparklineProps) {
  const series = values ?? data ?? [];
  return <span role="img" aria-label={ariaLabel} className={className} data-points={series.length} />;
}
