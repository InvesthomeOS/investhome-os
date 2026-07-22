export interface ProgressBarProps {
  value: number;
  max?: number;
  label?: string;
  tone?: 'default' | 'success' | 'warning' | 'danger' | 'gold';
  className?: string;
}

export function ProgressBar({
  value,
  max = 100,
  label,
  tone = 'default',
  className,
}: ProgressBarProps) {
  const pct = max <= 0 ? 0 : Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className={`ih-progress${className ? ` ${className}` : ''}`}>
      {label ? (
        <div className="ih-progress__meta">
          <span>{label}</span>
          <span>{Math.round(pct)}%</span>
        </div>
      ) : null}
      <div className="ih-progress__track" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={`ih-progress__fill ih-progress__fill--${tone}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
