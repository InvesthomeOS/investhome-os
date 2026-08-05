'use client';

import { useTranslations } from 'next-intl';

import { CsZoomControls } from '../_components/cs-zoom-controls';

export type SmbZoomControlsProps = {
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
export function SmbZoomControls({
  percent,
  onZoomOut,
  onZoomIn,
  onPercentChange,
  onReset,
  disabledOut,
  disabledIn,
  className,
}: SmbZoomControlsProps) {
  const t = useTranslations('creativeStudio.ds.socialMediaBuilder');
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
      className={['smb-zoom-controls', className].filter(Boolean).join(' ')}
      testIdPrefix="smb"
      ariaLabel={t('canvas.zoom')}
      zoomOutLabel={t('canvas.zoomOut')}
      zoomInLabel={t('canvas.zoomIn')}
      resetTitle={t('canvas.fitModes.actual')}
    />
  );
}
