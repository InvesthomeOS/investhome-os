/** Shared Fit-To-View engine — Figma/Canva-style stage scaling for all Creative Studio builders. */

export const CS_FOCUS_AUTO_FIT_KEY = 'cs-focus-auto-fit';

export const FIT_TO_VIEW_ZOOM_PRESETS = [50, 75, 100, 125, 150] as const;
export type FitToViewZoomPreset = (typeof FIT_TO_VIEW_ZOOM_PRESETS)[number];

/** View modes: Fit = entire artwork visible; Actual = 100% design px; Percent = absolute zoom. */
export type FitToViewMode = 'fit' | 'actual' | 'percent';

/**
 * Builder canvas strategy — defaults preserve approved layouts.
 * - artwork: contain entire frame (image, video, slide, page, social post)
 * - document: width-first readable column; height fills stage; content scrolls
 */
export type FitCanvasType = 'artwork' | 'document';

export type FitToViewPan = { x: number; y: number };

export type ComputeFitToViewInput = {
  availW: number;
  availH: number;
  contentWidth: number;
  contentHeight: number;
  mode: FitToViewMode;
  /** Absolute zoom percent relative to actual size (used by actual + percent; ignored by fit unless zooming off fit). */
  zoomPercent?: number;
  padX?: number;
  padY?: number;
  /** Defaults to artwork (contain). Document builders must opt in explicitly. */
  canvasType?: FitCanvasType;
};

export type FitToViewStageSize = {
  width: number;
  height: number;
  /** Display scale relative to intrinsic contentWidth (1 = actual size). */
  scale: number;
};

export function readAutoFitPreference(): boolean {
  if (typeof window === 'undefined') return true;
  try {
    const raw = window.localStorage.getItem(CS_FOCUS_AUTO_FIT_KEY);
    if (raw === null) return true;
    return raw !== '0';
  } catch {
    return true;
  }
}

export function writeAutoFitPreference(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(CS_FOCUS_AUTO_FIT_KEY, enabled ? '1' : '0');
  } catch {
    /* ignore */
  }
}

export function clampZoomPercent(value: number, min = 10, max = 400): number {
  if (!Number.isFinite(value)) return 100;
  return Math.min(max, Math.max(min, Math.round(value)));
}

export function nearestZoomPreset(value: number): FitToViewZoomPreset | null {
  const match = FIT_TO_VIEW_ZOOM_PRESETS.find((p) => p === value);
  return match ?? null;
}

/**
 * Compute display size so the entire artwork fits (or is shown at absolute zoom).
 * Fit never crops; aspect ratio is preserved for artwork. Grey workspace around artwork is OK.
 * Document strategy preserves readable width and uses stage height with vertical scroll.
 */
export function computeFitToViewStage(input: ComputeFitToViewInput): FitToViewStageSize {
  const contentW = Math.max(1, input.contentWidth);
  const contentH = Math.max(1, input.contentHeight);
  const ar = contentW / contentH;
  const zoom = clampZoomPercent(input.zoomPercent ?? 100) / 100;
  const padX = input.padX ?? 16;
  const padY = input.padY ?? 16;
  const availW = Math.max(80, input.availW - padX);
  const availH = Math.max(80, input.availH - padY);
  const canvasType = input.canvasType ?? 'artwork';

  if (canvasType === 'document') {
    if (input.mode === 'fit') {
      const width = Math.min(contentW, availW);
      return {
        width,
        height: availH,
        scale: width / contentW,
      };
    }
    const width = Math.min(contentW * zoom, availW);
    return {
      width,
      height: availH,
      scale: width / contentW,
    };
  }

  if (input.mode === 'fit') {
    let width = availW;
    let height = width / ar;
    if (height > availH) {
      height = availH;
      width = height * ar;
    }
    return {
      width,
      height,
      scale: width / contentW,
    };
  }

  // actual | percent — absolute zoom relative to design pixels
  const width = contentW * zoom;
  const height = contentH * zoom;
  return { width, height, scale: zoom };
}

/** Legacy bridge: map older fit/fill/actual + zoom multiplier into Fit-To-View stage size. */
export function computeFitCanvasStage(input: {
  availW: number;
  availH: number;
  aspectRatio: number;
  mode: 'fit' | 'fill' | 'actual';
  zoom?: number;
  actualWidth?: number;
  padX?: number;
  padY?: number;
}): { width: number; height: number } {
  const ar = input.aspectRatio > 0 ? input.aspectRatio : 1;
  const actualW = input.actualWidth ?? 794;
  const actualH = actualW / ar;
  const padX = input.padX ?? (input.mode === 'fill' ? 8 : 16);
  const padY = input.padY ?? (input.mode === 'fill' ? 8 : 16);
  const zoomPercent = Math.round((input.zoom ?? 1) * 100);

  if (input.mode === 'fill') {
    // Fill = tighter padding fit (legacy)
    const size = computeFitToViewStage({
      availW: input.availW,
      availH: input.availH,
      contentWidth: actualW,
      contentHeight: actualH,
      mode: 'fit',
      zoomPercent: 100,
      padX,
      padY,
      canvasType: 'artwork',
    });
    return { width: size.width * (zoomPercent / 100), height: size.height * (zoomPercent / 100) };
  }

  const size = computeFitToViewStage({
    availW: input.availW,
    availH: input.availH,
    contentWidth: actualW,
    contentHeight: actualH,
    mode: input.mode === 'actual' ? 'actual' : 'fit',
    zoomPercent,
    padX,
    padY,
    canvasType: 'artwork',
  });
  return { width: size.width, height: size.height };
}
