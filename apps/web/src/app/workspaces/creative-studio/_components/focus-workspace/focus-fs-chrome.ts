/** Shared Fullscreen Focus canvas chrome — tray, dock, pin preference, ESC layers. */

export const CS_FOCUS_PIN_BOTTOM_KEY = 'cs-focus-pin-bottom-tools';

export type FocusFsDisplayMode = 'fit' | 'fill' | 'actual' | 'custom';

export type FocusFsEscLayerId = 'tray' | 'dockOverflow' | 'dock';

export type FocusFsEscLayer = {
  id: FocusFsEscLayerId;
  /** Higher runs first. tray=40, dockOverflow=30, dock=20 */
  priority: number;
  isActive: () => boolean;
  close: () => void;
};

const escLayers = new Map<FocusFsEscLayerId, FocusFsEscLayer>();

export function registerFocusFsEscLayer(layer: FocusFsEscLayer): () => void {
  escLayers.set(layer.id, layer);
  return () => {
    if (escLayers.get(layer.id) === layer) {
      escLayers.delete(layer.id);
    }
  };
}

/** Close the highest-priority active FS chrome layer. Returns true if something closed. */
export function tryCloseFocusFsEscLayer(): boolean {
  const ordered = [...escLayers.values()].sort((a, b) => b.priority - a.priority);
  for (const layer of ordered) {
    if (layer.isActive()) {
      layer.close();
      return true;
    }
  }
  return false;
}

export function readPinBottomTools(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return window.localStorage.getItem(CS_FOCUS_PIN_BOTTOM_KEY) === '1';
  } catch {
    return false;
  }
}

export function writePinBottomTools(pinned: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(CS_FOCUS_PIN_BOTTOM_KEY, pinned ? '1' : '0');
  } catch {
    /* ignore */
  }
}

export type { FitToViewMode, FitToViewZoomPreset, FitToViewPan, FitToViewStageSize, FitCanvasType } from './fit-to-view-engine';
export {
  CS_FOCUS_AUTO_FIT_KEY,
  FIT_TO_VIEW_ZOOM_PRESETS,
  clampZoomPercent,
  computeFitToViewStage,
  nearestZoomPreset,
  readAutoFitPreference,
  writeAutoFitPreference,
  computeFitCanvasStage,
} from './fit-to-view-engine';

export type FitCanvasStageInput = {
  availW: number;
  availH: number;
  /** width / height */
  aspectRatio: number;
  mode: 'fit' | 'fill' | 'actual';
  zoom?: number;
  actualWidth?: number;
  padX?: number;
  padY?: number;
};

export type FitCanvasStageSize = { width: number; height: number };
