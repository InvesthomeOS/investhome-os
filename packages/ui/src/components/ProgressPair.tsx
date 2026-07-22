import { ProgressBar, type ProgressBarProps } from './ProgressBar.js';

export interface ProgressPairItem {
  label: string;
  value: number;
  max?: number;
  tone?: ProgressBarProps['tone'];
}

export interface ProgressPairProps {
  /** Construction progress */
  construction: ProgressPairItem;
  /** Sales progress */
  sales: ProgressPairItem;
  className?: string;
}

/**
 * Two progress indicators for project cards (UXR1 V2 §08):
 * Construction Progress + Sales Progress.
 */
export function ProgressPair({ construction, sales, className }: ProgressPairProps) {
  return (
    <div className={`ds-progress-pair${className ? ` ${className}` : ''}`}>
      <ProgressBar
        label={construction.label}
        value={construction.value}
        max={construction.max}
        tone={construction.tone ?? 'default'}
      />
      <ProgressBar
        label={sales.label}
        value={sales.value}
        max={sales.max}
        tone={sales.tone ?? 'success'}
      />
    </div>
  );
}
