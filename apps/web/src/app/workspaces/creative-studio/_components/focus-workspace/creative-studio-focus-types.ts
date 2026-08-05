import type { IhIconName } from '@/components/icons/ih-icons';

/** Global Creative Studio workspace viewing modes. */
export type CreativeStudioWorkspaceMode = 'normal' | 'focus' | 'preview';

export type FocusRailSide = 'left' | 'right';

export type FocusRailItem = {
  id: string;
  icon: IhIconName;
  /** i18n key under creativeStudio.focusWorkspace.rails.* */
  labelKey: string;
  /**
   * Optional display label override (builder-specific).
   * When set, used instead of focusWorkspace.rails[labelKey] — keeps shared defaults intact.
   */
  label?: string;
};

export type FocusWorkspaceApi = {
  mode: CreativeStudioWorkspaceMode;
  setMode: (mode: CreativeStudioWorkspaceMode) => void;
  isPreview: boolean;
  isFocus: boolean;
  isNormal: boolean;
  /** Fullscreen Focus Workspace (Focus Mode + viewport shell). Not Clean Preview. */
  isFullscreen: boolean;
  enterFullscreen: () => void;
  exitFullscreen: () => void;
  toggleFullscreen: () => void;
};

export const CS_FOCUS_STORAGE_PREFIX = 'cs-focus-workspace-mode:';

export const CS_FOCUS_LEFT_RAIL: FocusRailItem[] = [
  { id: 'brief', icon: 'documents', labelKey: 'brief' },
  { id: 'assets', icon: 'inventory', labelKey: 'assets' },
  { id: 'brand', icon: 'design', labelKey: 'brand' },
  { id: 'settings', icon: 'settings', labelKey: 'settings' },
  { id: 'advanced', icon: 'sparkles', labelKey: 'advanced' },
];

export const CS_FOCUS_RIGHT_RAIL: FocusRailItem[] = [
  { id: 'score', icon: 'trendingUp', labelKey: 'score' },
  { id: 'suggestions', icon: 'sparkles', labelKey: 'suggestions' },
  { id: 'quickActions', icon: 'quickAction', labelKey: 'quickActions' },
  { id: 'export', icon: 'inbox', labelKey: 'export' },
  { id: 'history', icon: 'clock', labelKey: 'history' },
];

export const CS_FOCUS_MODE_ORDER: CreativeStudioWorkspaceMode[] = [
  'normal',
  'focus',
  'preview',
];

export const CS_FOCUS_MODE_ICONS: Record<CreativeStudioWorkspaceMode, IhIconName> = {
  normal: 'projects',
  focus: 'target',
  preview: 'design',
};
