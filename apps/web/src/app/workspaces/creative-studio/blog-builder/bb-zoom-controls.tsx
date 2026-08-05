'use client';

import { useTranslations } from 'next-intl';

import { CsZoomControls } from '../_components/cs-zoom-controls';

export type BbZoomControlsProps = {
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
export function BbZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onPercentChange,
  onReset,
  disabledOut,
  disabledIn,
  className,
}: BbZoomControlsProps) {
  const t = useTranslations('creativeStudio.ds.blogBuilder');
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
      className={['bb-zoom-controls', className].filter(Boolean).join(' ')}
      testIdPrefix="bb"
      ariaLabel={t('canvas.zoom')}
      zoomOutLabel={t('canvas.zoomOut')}
      zoomInLabel={t('canvas.zoomIn')}
      resetTitle={t('canvas.fitModes.actual')}
    />
  );
}
