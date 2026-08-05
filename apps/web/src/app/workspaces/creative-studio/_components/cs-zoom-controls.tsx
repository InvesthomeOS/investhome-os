'use client';

/**
 * Shared Creative Studio zoom stepper: [−] 100% [+]
 * Replaces per-builder clones and FTV preset chip rows.
 */

export type CsZoomControlsProps = {
  percent: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
  /** Click percent label — typically Actual Size / 100%. */
  onReset?: () => void;
  disabledOut?: boolean;
  disabledIn?: boolean;
  className?: string;
  /** Prefix for data-testid attributes (e.g. "pb" → pb-zoom-controls). */
  testIdPrefix?: string;
  ariaLabel: string;
  zoomOutLabel: string;
  zoomInLabel: string;
  resetTitle?: string;
};

export function CsZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onReset,
  disabledOut,
  disabledIn,
  className,
  testIdPrefix = 'cs',
  ariaLabel,
  zoomOutLabel,
  zoomInLabel,
  resetTitle,
}: CsZoomControlsProps) {
  const rootClass = ['cs-zoom-controls', className].filter(Boolean).join(' ');

  return (
    <div
      className={rootClass}
      role="group"
      aria-label={ariaLabel}
      data-testid={`${testIdPrefix}-zoom-controls`}
    >
      <button
        type="button"
        className="cs-zoom-controls__btn"
        aria-label={zoomOutLabel}
        title={zoomOutLabel}
        data-testid={`${testIdPrefix}-zoom-out`}
        disabled={disabledOut}
        onClick={onZoomOut}
      >
        −
      </button>
      <button
        type="button"
        className="cs-zoom-controls__value"
        aria-label={ariaLabel}
        data-testid={`${testIdPrefix}-zoom-percent`}
        title={onReset ? resetTitle : undefined}
        onClick={onReset}
      >
        {Math.round(percent)}%
      </button>
      <button
        type="button"
        className="cs-zoom-controls__btn"
        aria-label={zoomInLabel}
        title={zoomInLabel}
        data-testid={`${testIdPrefix}-zoom-in`}
        disabled={disabledIn}
        onClick={onZoomIn}
      >
        +
      </button>
    </div>
  );
}
