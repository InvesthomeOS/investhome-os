export type TrendDirection = 'up' | 'down' | 'neutral';

export interface TrendIndicatorProps {
  direction: TrendDirection;
  label: string;
  className?: string;
}

export function TrendIndicator({ direction, label, className }: TrendIndicatorProps) {
  return (
    <span className={`ds-trend ds-trend--${direction}${className ? ` ${className}` : ''}`}>
      <span className="ds-trend__arrow" aria-hidden="true">
        {direction === 'up' ? '▲' : direction === 'down' ? '▼' : '•'}
      </span>
      {label}
    </span>
  );
}
