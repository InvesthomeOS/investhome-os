'use client';

import { useTranslations } from 'next-intl';

import { CsZoomControls } from '../_components/cs-zoom-controls';

export type PbZoomControlsProps = {
  percent: number;
  onZoomOut: () => void;
  onZoomIn: () => void;
  onReset?: () => void;
  disabledOut?: boolean;
  disabledIn?: boolean;
  className?: string;
};

/** Thin wrapper — shared CsZoomControls (− / % / +). */
export function PbZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onReset,
  disabledOut,
  disabledIn,
  className,
}: PbZoomControlsProps) {
  const t = useTranslations('creativeStudio.ds.presentationBuilder');
  return (
    <CsZoomControls
      percent={percent}
      onZoomOut={onZoomOut}
      onZoomIn={onZoomIn}
      onReset={onReset}
      disabledOut={disabledOut}
      disabledIn={disabledIn}
      className={['pb-zoom-controls', className].filter(Boolean).join(' ')}
      testIdPrefix="pb"
      ariaLabel={t('canvas.zoom')}
      zoomOutLabel={t('canvas.zoomOut')}
      zoomInLabel={t('canvas.zoomIn')}
      resetTitle={t('canvas.fitModes.actual')}
    />
  );
}
