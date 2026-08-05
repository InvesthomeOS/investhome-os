'use client';

import {
  useCallback,
  useEffect,
  useRef,
  type RefObject,
} from 'react';

import {
  computeFitCanvasStage,
  type FitCanvasStageSize,
} from './focus-fs-chrome';

export type UseFitCanvasStageOptions = {
  /** Aspect ratio width/height (e.g. 210/297 for A4). */
  aspectRatio: number;
  mode: 'fit' | 'fill' | 'actual';
  zoom?: number;
  actualWidth?: number;
  /** When true, always height-clamp (FS Fit). When false, width-first (legacy scroll). */
  heightAware: boolean;
  enabled?: boolean;
  cssWidthVar?: string;
  cssHeightVar?: string;
  onSize?: (size: FitCanvasStageSize) => void;
};

/**
 * Observe a mat/stage element and set CSS size vars so the canvas fits available space.
 */
export function useFitCanvasStage(
  matRef: RefObject<HTMLElement | null>,
  {
    aspectRatio,
    mode,
    zoom = 1,
    actualWidth,
    heightAware,
    enabled = true,
    cssWidthVar = '--cs-fw-stage-w',
    cssHeightVar = '--cs-fw-stage-h',
    onSize,
  }: UseFitCanvasStageOptions,
) {
  const onSizeRef = useRef(onSize);
  onSizeRef.current = onSize;

  const fit = useCallback(() => {
    const mat = matRef.current;
    if (!mat || !enabled) return;

    const rect = mat.getBoundingClientRect();
    const availW = Math.max(120, rect.width);
    const availH = heightAware
      ? Math.max(90, rect.height)
      : Math.max(90, Math.min(rect.height || 900, 2400));

    let size: FitCanvasStageSize;
    if (!heightAware && mode === 'fit') {
      // Legacy width-preferred document sizing (non-FS) — still set height from AR
      const pad = 32;
      const baseW = Math.min(680, Math.max(260, availW - pad));
      const width = baseW * zoom;
      size = { width, height: width / aspectRatio };
    } else {
      size = computeFitCanvasStage({
        availW,
        availH: heightAware ? availH : availH,
        aspectRatio,
        mode,
        zoom,
        actualWidth,
      });
    }

    mat.style.setProperty(cssWidthVar, `${Math.round(size.width)}px`);
    mat.style.setProperty(cssHeightVar, `${Math.round(size.height)}px`);
    onSizeRef.current?.(size);
  }, [
    matRef,
    aspectRatio,
    mode,
    zoom,
    actualWidth,
    heightAware,
    enabled,
    cssWidthVar,
    cssHeightVar,
  ]);

  useEffect(() => {
    const mat = matRef.current;
    if (!mat || !enabled) return;
    fit();
    const ro = new ResizeObserver(() => fit());
    ro.observe(mat);
    window.addEventListener('resize', fit);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', fit);
    };
  }, [matRef, fit, enabled]);

  return { refit: fit };
}
