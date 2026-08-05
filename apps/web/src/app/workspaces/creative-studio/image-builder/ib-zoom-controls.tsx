'use client';

import { useTranslations } from 'next-intl';

import { CsZoomControls } from '../_components/cs-zoom-controls';

export type IbZoomControlsProps = {
  percent: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onReset?: () => void;
  disabledOut?: boolean;
  disabledIn?: boolean;
  className?: string;
};

/** Thin wrapper — shared CsZoomControls (− / % / +). */
export function IbZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onReset,
  disabledOut,
  disabledIn,
  className,
}: IbZoomControlsProps) {
  const t = useTranslations('creativeStudio.ds.imageBuilder');
  return (
    <CsZoomControls
      percent={percent}
      onZoomOut={onZoomOut}
      onZoomIn={onZoomIn}
      onReset={onReset}
      disabledOut={disabledOut}
      disabledIn={disabledIn}
      className={['ib-zoom-controls', className].filter(Boolean).join(' ')}
      testIdPrefix="ib"
      ariaLabel={t('canvas.zoom')}
      zoomOutLabel={t('canvas.zoomOut')}
      zoomInLabel={t('canvas.zoomIn')}
      resetTitle={t('canvas.fitModes.actual')}
    />
  );
}
