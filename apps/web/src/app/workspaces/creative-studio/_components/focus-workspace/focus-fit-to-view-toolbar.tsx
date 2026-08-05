'use client';

import { useTranslations } from 'next-intl';

import type { FitToViewEngineApi } from './use-fit-to-view-engine';
import { CsZoomControls } from '../cs-zoom-controls';

export type FocusFitToViewToolbarProps = {
  engine: FitToViewEngineApi;
  className?: string;
  /** Hide Auto Fit checkbox (rare). Default shows it. */
  showAutoFit?: boolean;
};

const ZOOM_STEP = 25;
const ZOOM_MIN = 25;
const ZOOM_MAX = 200;

/**
 * Compact shared Fit-To-View controls:
 * Fit To View · Actual Size · [−] % [+] · Auto Fit
 * (Preset chip rows removed — Phase 1 zoom standard.)
 */
export function FocusFitToViewToolbar({
  engine,
  className,
  showAutoFit = true,
}: FocusFitToViewToolbarProps) {
  const t = useTranslations('creativeStudio.focusWorkspace.fitToView');

  const rootClass = ['cs-ftv-toolbar', className].filter(Boolean).join(' ');
  const { mode, zoomPercent, autoFit } = engine;
  const percent = Math.round(zoomPercent);

  function zoomBy(delta: number) {
    engine.setPercent(Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, percent + delta)));
  }

  return (
    <div
      className={rootClass}
      role="toolbar"
      aria-label={t('aria')}
      data-testid="cs-ftv-toolbar"
    >
      <div className="cs-ftv-toolbar__modes" role="group" aria-label={t('modesAria')}>
        <button
          type="button"
          className={`cs-ftv-toolbar__btn${mode === 'fit' ? ' is-active' : ''}`}
          aria-pressed={mode === 'fit'}
          data-testid="cs-ftv-fit"
          onClick={() => engine.fitToView()}
        >
          {t('fit')}
        </button>
        <button
          type="button"
          className={`cs-ftv-toolbar__btn${mode === 'actual' ? ' is-active' : ''}`}
          aria-pressed={mode === 'actual'}
          data-testid="cs-ftv-actual"
          onClick={() => engine.actualSize()}
        >
          {t('actual')}
        </button>
      </div>

      <div className="cs-ftv-toolbar__zoom" role="group" aria-label={t('zoomAria')}>
        <CsZoomControls
          percent={percent}
          disabledOut={percent <= ZOOM_MIN}
          disabledIn={percent >= ZOOM_MAX}
          onZoomOut={() => zoomBy(-ZOOM_STEP)}
          onZoomIn={() => zoomBy(ZOOM_STEP)}
          onReset={() => engine.actualSize()}
          testIdPrefix="cs-ftv"
          ariaLabel={t('zoomAria')}
          zoomOutLabel={t('zoomOut')}
          zoomInLabel={t('zoomIn')}
          resetTitle={t('actual')}
          className="cs-ftv-toolbar__stepper"
        />
      </div>

      {showAutoFit ? (
        <label className="cs-ftv-toolbar__auto" data-testid="cs-ftv-auto-fit">
          <input
            type="checkbox"
            checked={autoFit}
            onChange={(e) => engine.setAutoFit(e.target.checked)}
          />
          <span>{t('autoFit')}</span>
        </label>
      ) : null}
    </div>
  );
}
