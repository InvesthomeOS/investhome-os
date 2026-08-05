'use client';

import { useTranslations } from 'next-intl';

import { CsZoomControls } from '../_components/cs-zoom-controls';

export type LpbZoomControlsProps = {
  percent: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onPercentChange?: (percent: number) => void;
  onReset?: () => void;
  disabledOut?: boolean;
  disabledIn?: boolean;
  className?: string;
};

/** Thin wrapper — shared CsZoomControls (− / % / +). */
export function LpbZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onPercentChange,
  onReset,
  disabledOut,
  disabledIn,
  className,
}: LpbZoomControlsProps) {
  const t = useTranslations('creativeStudio.ds.landingPageBuilder');
  const handleReset =
    onReset ??
    (onPercentChange
      ? () => {
          onPercentChange(100);
        }
      : undefined);
  return (
    <CsZoomControls
      percent={percent}
      onZoomOut={onZoomOut}
      onZoomIn={onZoomIn}
      onReset={handleReset}
      disabledOut={disabledOut}
      disabledIn={disabledIn}
      className={['lpb-zoom-controls', className].filter(Boolean).join(' ')}
      testIdPrefix="lpb"
      ariaLabel={t('canvas.zoom')}
      zoomOutLabel={t('canvas.zoomOut')}
      zoomInLabel={t('canvas.zoomIn')}
      resetTitle={t('canvas.fitModes.actual')}
    />
  );
}
