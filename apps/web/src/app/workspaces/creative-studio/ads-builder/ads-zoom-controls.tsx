'use client';

import { useTranslations } from 'next-intl';

import { CsZoomControls } from '../_components/cs-zoom-controls';

export type AdsZoomControlsProps = {
  percent: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
  /** @deprecated Prefer onReset — select presets removed in Phase 1. */
  onPercentChange?: (percent: number) => void;
  onReset?: () => void;
  disabledOut?: boolean;
  disabledIn?: boolean;
  className?: string;
};

/** Thin wrapper — shared CsZoomControls (− / % / +). */
export function AdsZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onPercentChange,
  onReset,
  disabledOut,
  disabledIn,
  className,
}: AdsZoomControlsProps) {
  const t = useTranslations('creativeStudio.ds.adsBuilder');
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
      className={['ads-zoom-controls', className].filter(Boolean).join(' ')}
      testIdPrefix="ads"
      ariaLabel={t('canvas.zoom')}
      zoomOutLabel={t('canvas.zoomOut')}
      zoomInLabel={t('canvas.zoomIn')}
      resetTitle={t('canvas.fitModes.actual')}
    />
  );
}
