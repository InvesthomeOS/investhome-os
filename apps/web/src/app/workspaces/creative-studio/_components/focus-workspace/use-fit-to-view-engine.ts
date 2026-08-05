'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type RefObject,
  type WheelEvent as ReactWheelEvent,
} from 'react';

import {
  clampZoomPercent,
  computeFitToViewStage,
  FIT_TO_VIEW_ZOOM_PRESETS,
  nearestZoomPreset,
  readAutoFitPreference,
  writeAutoFitPreference,
  type FitCanvasType,
  type FitToViewMode,
  type FitToViewPan,
  type FitToViewStageSize,
  type FitToViewZoomPreset,
} from './fit-to-view-engine';

export type UseFitToViewEngineOptions = {
  /** Intrinsic artwork width in design pixels (e.g. 1080, 794). */
  contentWidth: number;
  /** Intrinsic artwork height in design pixels (e.g. 1350, 1123). */
  contentHeight: number;
  /**
   * When true, engine is active (Focus / Fullscreen / large-art Normal).
   * When false, still exposes API but prefers fit sizing without interaction capture.
   */
  enabled?: boolean;
  /** Change triggers Auto Fit re-entry when autoFit is on. */
  contentKey?: string | number;
  padX?: number;
  padY?: number;
  /**
   * Canvas sizing strategy. Default `artwork` preserves approved image/video/slide/page layouts.
   * Document builders (blog, email, website, landing) must pass `document` explicitly.
   */
  canvasType?: FitCanvasType;
  /** CSS vars written onto the viewport element for builders that size via vars. */
  cssWidthVar?: string;
  cssHeightVar?: string;
  cssScaleVar?: string;
  onSize?: (size: FitToViewStageSize) => void;
};

export type FitToViewEngineApi = {
  mode: FitToViewMode;
  zoomPercent: number;
  autoFit: boolean;
  pan: FitToViewPan;
  stageSize: FitToViewStageSize;
  spacePanActive: boolean;
  canvasType: FitCanvasType;
  viewportRef: RefObject<HTMLDivElement | null>;
  setMode: (mode: FitToViewMode) => void;
  setZoomPercent: (percent: number) => void;
  setAutoFit: (enabled: boolean) => void;
  fitToView: () => void;
  actualSize: () => void;
  setPercent: (percent: FitToViewZoomPreset | number) => void;
  resetPan: () => void;
  refit: () => void;
  /** Attach to the viewport/stage element. */
  viewportProps: {
    ref: RefObject<HTMLDivElement | null>;
    onWheel: (event: ReactWheelEvent<HTMLDivElement>) => void;
    onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerMove: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerUp: (event: ReactPointerEvent<HTMLDivElement>) => void;
    onPointerCancel: (event: ReactPointerEvent<HTMLDivElement>) => void;
    'data-ftv-mode': FitToViewMode;
    'data-ftv-auto-fit': string;
    'data-ftv-zoom': string;
    'data-ftv-canvas': FitCanvasType;
    'data-testid': string;
  };
};

/**
 * Single Fit-To-View engine for all Creative Studio builders.
 * Default = Fit (entire artwork visible). Auto Fit persists via localStorage.
 * Ctrl+wheel zooms; Space+drag pans.
 */
export function useFitToViewEngine({
  contentWidth,
  contentHeight,
  enabled = true,
  contentKey,
  padX = 20,
  padY = 16,
  canvasType = 'artwork',
  cssWidthVar = '--cs-ftv-w',
  cssHeightVar = '--cs-ftv-h',
  cssScaleVar = '--cs-ftv-scale',
  onSize,
}: UseFitToViewEngineOptions): FitToViewEngineApi {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [mode, setModeState] = useState<FitToViewMode>('fit');
  const [zoomPercent, setZoomPercentState] = useState(100);
  const [autoFit, setAutoFitState] = useState(true);
  const [pan, setPan] = useState<FitToViewPan>({ x: 0, y: 0 });
  const [stageSize, setStageSize] = useState<FitToViewStageSize>({
    width: contentWidth,
    height: contentHeight,
    scale: 1,
  });
  const [spacePanActive, setSpacePanActive] = useState(false);
  const draggingRef = useRef(false);
  const lastPointerRef = useRef({ x: 0, y: 0 });
  const onSizeRef = useRef(onSize);
  onSizeRef.current = onSize;
  const modeRef = useRef(mode);
  modeRef.current = mode;
  const zoomRef = useRef(zoomPercent);
  zoomRef.current = zoomPercent;
  const autoFitRef = useRef(autoFit);
  autoFitRef.current = autoFit;
  const canvasTypeRef = useRef(canvasType);
  canvasTypeRef.current = canvasType;

  useEffect(() => {
    setAutoFitState(readAutoFitPreference());
  }, []);

  const applySize = useCallback(
    (size: FitToViewStageSize) => {
      setStageSize(size);
      const el = viewportRef.current;
      if (el) {
        el.style.setProperty(cssWidthVar, `${Math.round(size.width)}px`);
        el.style.setProperty(cssHeightVar, `${Math.round(size.height)}px`);
        el.style.setProperty(cssScaleVar, String(size.scale));
      }
      onSizeRef.current?.(size);
    },
    [cssWidthVar, cssHeightVar, cssScaleVar],
  );

  const refit = useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const size = computeFitToViewStage({
      availW: Math.max(120, rect.width),
      availH: Math.max(90, rect.height),
      contentWidth,
      contentHeight,
      mode: modeRef.current,
      zoomPercent: zoomRef.current,
      padX,
      padY,
      canvasType: canvasTypeRef.current,
    });
    applySize(size);
  }, [applySize, contentWidth, contentHeight, padX, padY, canvasType]);

  const fitToView = useCallback(() => {
    setModeState('fit');
    setZoomPercentState(100);
    setPan({ x: 0, y: 0 });
    modeRef.current = 'fit';
    zoomRef.current = 100;
    // defer measure to next frame so mode is committed
    requestAnimationFrame(() => refit());
  }, [refit]);

  const actualSize = useCallback(() => {
    setModeState('actual');
    setZoomPercentState(100);
    setPan({ x: 0, y: 0 });
    modeRef.current = 'actual';
    zoomRef.current = 100;
    requestAnimationFrame(() => refit());
  }, [refit]);

  const setPercent = useCallback(
    (percent: FitToViewZoomPreset | number) => {
      const next = clampZoomPercent(percent);
      setModeState('percent');
      setZoomPercentState(next);
      modeRef.current = 'percent';
      zoomRef.current = next;
      requestAnimationFrame(() => refit());
    },
    [refit],
  );

  const setMode = useCallback(
    (next: FitToViewMode) => {
      if (next === 'fit') fitToView();
      else if (next === 'actual') actualSize();
      else setPercent(zoomRef.current);
    },
    [fitToView, actualSize, setPercent],
  );

  const setZoomPercent = useCallback(
    (percent: number) => {
      setPercent(percent);
    },
    [setPercent],
  );

  const setAutoFit = useCallback(
    (value: boolean) => {
      setAutoFitState(value);
      autoFitRef.current = value;
      writeAutoFitPreference(value);
      if (value) fitToView();
    },
    [fitToView],
  );

  const resetPan = useCallback(() => setPan({ x: 0, y: 0 }), []);

  // Auto Fit on enable / content change
  useEffect(() => {
    if (!enabled) return;
    if (autoFitRef.current) {
      fitToView();
    } else {
      refit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- contentKey intentionally triggers re-fit
  }, [enabled, contentKey, contentWidth, contentHeight, fitToView, refit]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el) return;
    refit();
    const ro = new ResizeObserver(() => {
      // Always remeasure — document canvases need height = stage; artwork needs contain.
      refit();
    });
    ro.observe(el);
    window.addEventListener('resize', refit);
    return () => {
      ro.disconnect();
      window.removeEventListener('resize', refit);
    };
  }, [refit, enabled]);

  // Space = pan grab
  useEffect(() => {
    if (!enabled) return;
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const editing =
        tag === 'input' ||
        tag === 'textarea' ||
        tag === 'select' ||
        target?.isContentEditable;
      if (editing) return;
      if (event.code === 'Space' && !event.repeat) {
        event.preventDefault();
        setSpacePanActive(true);
      }
    }
    function onKeyUp(event: KeyboardEvent) {
      if (event.code === 'Space') {
        setSpacePanActive(false);
        draggingRef.current = false;
      }
    }
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [enabled]);

  const onWheel = useCallback(
    (event: ReactWheelEvent<HTMLDivElement>) => {
      if (!enabled) return;
      if (!event.ctrlKey && !event.metaKey) return;
      event.preventDefault();
      event.stopPropagation();

      const delta = event.deltaY > 0 ? -10 : 10;
      const base =
        modeRef.current === 'fit'
          ? Math.round(stageSize.scale * 100)
          : zoomRef.current;
      const next = clampZoomPercent(base + delta);
      setModeState('percent');
      setZoomPercentState(next);
      modeRef.current = 'percent';
      zoomRef.current = next;
      // Leave auto-fit visual lock when user manually zooms
      requestAnimationFrame(() => refit());
    },
    [enabled, refit, stageSize.scale],
  );

  const onPointerDown = useCallback(
    (event: ReactPointerEvent<HTMLDivElement>) => {
      if (!enabled) return;
      if (!spacePanActive && event.button !== 1) return;
      event.preventDefault();
      draggingRef.current = true;
      lastPointerRef.current = { x: event.clientX, y: event.clientY };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [enabled, spacePanActive],
  );

  const onPointerMove = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    if (!draggingRef.current) return;
    const dx = event.clientX - lastPointerRef.current.x;
    const dy = event.clientY - lastPointerRef.current.y;
    lastPointerRef.current = { x: event.clientX, y: event.clientY };
    setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
  }, []);

  const onPointerUp = useCallback((event: ReactPointerEvent<HTMLDivElement>) => {
    draggingRef.current = false;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  }, []);

  return {
    mode,
    zoomPercent,
    autoFit,
    pan,
    stageSize,
    spacePanActive,
    canvasType,
    viewportRef,
    setMode,
    setZoomPercent,
    setAutoFit,
    fitToView,
    actualSize,
    setPercent,
    resetPan,
    refit,
    viewportProps: {
      ref: viewportRef,
      onWheel,
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onPointerCancel: onPointerUp,
      'data-ftv-mode': mode,
      'data-ftv-auto-fit': autoFit ? 'true' : 'false',
      'data-ftv-zoom': String(zoomPercent),
      'data-ftv-canvas': canvasType,
      'data-testid': 'cs-ftv-viewport',
    },
  };
}

export { FIT_TO_VIEW_ZOOM_PRESETS, nearestZoomPreset };
