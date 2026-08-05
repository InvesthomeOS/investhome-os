/** Global Focus Mode Framework — shared workspace viewing system for all Creative Studio builders. */
export type {
  CreativeStudioWorkspaceMode,
  FocusRailItem,
  FocusRailSide,
  FocusWorkspaceApi,
} from './creative-studio-focus-types';
export {
  CS_FOCUS_LEFT_RAIL,
  CS_FOCUS_RIGHT_RAIL,
  CS_FOCUS_MODE_ICONS,
  CS_FOCUS_MODE_ORDER,
  CS_FOCUS_STORAGE_PREFIX,
} from './creative-studio-focus-types';
export { CreativeStudioFocusModeSwitcher } from './creative-studio-focus-mode-switcher';
export { CreativeStudioFocusWorkspace } from './creative-studio-focus-workspace';
export { useCreativeStudioFocusMode } from './use-creative-studio-focus-mode';
export {
  CS_FOCUS_PIN_BOTTOM_KEY,
  CS_FOCUS_AUTO_FIT_KEY,
  FIT_TO_VIEW_ZOOM_PRESETS,
  clampZoomPercent,
  computeFitCanvasStage,
  computeFitToViewStage,
  nearestZoomPreset,
  readAutoFitPreference,
  readPinBottomTools,
  registerFocusFsEscLayer,
  tryCloseFocusFsEscLayer,
  writeAutoFitPreference,
  writePinBottomTools,
} from './focus-fs-chrome';
export type {
  FitCanvasStageInput,
  FitCanvasStageSize,
  FitCanvasType,
  FitToViewMode,
  FitToViewPan,
  FitToViewStageSize,
  FitToViewZoomPreset,
  FocusFsDisplayMode,
  FocusFsEscLayer,
  FocusFsEscLayerId,
} from './focus-fs-chrome';
export { FocusCanvasLayout } from './focus-canvas-layout';
export type {
  FocusCanvasDockSlot,
  FocusCanvasLayoutProps,
  FocusCanvasTraySlot,
} from './focus-canvas-layout';
export { FocusSecondaryTray } from './focus-secondary-tray';
export { FocusActionDock } from './focus-action-dock';
export { useFocusFsChrome } from './use-focus-fs-chrome';
export { useFitCanvasStage } from './use-fit-canvas-stage';
export { useFitToViewEngine } from './use-fit-to-view-engine';
export type {
  FitToViewEngineApi,
  UseFitToViewEngineOptions,
} from './use-fit-to-view-engine';
export { FocusFitStage } from './focus-fit-stage';
export type { FocusFitStageProps } from './focus-fit-stage';
export { FocusFitToViewToolbar } from './focus-fit-to-view-toolbar';
export type { FocusFitToViewToolbarProps } from './focus-fit-to-view-toolbar';
