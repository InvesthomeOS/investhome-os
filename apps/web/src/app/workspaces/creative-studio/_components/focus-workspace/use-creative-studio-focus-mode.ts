'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  CS_FOCUS_STORAGE_PREFIX,
  type CreativeStudioWorkspaceMode,
  type FocusWorkspaceApi,
} from './creative-studio-focus-types';

function isMode(value: string | null | undefined): value is CreativeStudioWorkspaceMode {
  return value === 'normal' || value === 'focus' || value === 'preview';
}

export type UseCreativeStudioFocusModeOptions = {
  /** Persistence key suffix, e.g. "proposal-builder". */
  storageKey: string;
  defaultMode?: CreativeStudioWorkspaceMode;
  /** When false, mode is session-only (default: persist). */
  persist?: boolean;
};

/**
 * Shared workspace mode state + keyboard shortcuts for all Creative Studio builders.
 * Shift+1 Normal · Shift+2 Focus · Shift+3 Preview · ESC exits Preview.
 * Fullscreen Focus is orthogonal: forces Focus Mode + fullscreen shell (rails stay visible).
 */
export function useCreativeStudioFocusMode({
  storageKey,
  defaultMode = 'normal',
  persist = true,
}: UseCreativeStudioFocusModeOptions): FocusWorkspaceApi {
  const fullKey = `${CS_FOCUS_STORAGE_PREFIX}${storageKey}`;
  const [mode, setModeState] = useState<CreativeStudioWorkspaceMode>(defaultMode);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (!persist || typeof window === 'undefined') return;
    try {
      const stored = window.localStorage.getItem(fullKey);
      if (isMode(stored)) setModeState(stored);
    } catch {
      /* ignore */
    }
  }, [fullKey, persist]);

  const setMode = useCallback(
    (next: CreativeStudioWorkspaceMode) => {
      setModeState(next);
      // Fullscreen Focus only coexists with Focus Mode (not Normal / Clean Preview)
      if (next !== 'focus') {
        setIsFullscreen(false);
      }
      if (!persist || typeof window === 'undefined') return;
      try {
        window.localStorage.setItem(fullKey, next);
      } catch {
        /* ignore */
      }
    },
    [fullKey, persist],
  );

  const enterFullscreen = useCallback(() => {
    setModeState('focus');
    setIsFullscreen(true);
    if (!persist || typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(fullKey, 'focus');
    } catch {
      /* ignore */
    }
  }, [fullKey, persist]);

  const exitFullscreen = useCallback(() => {
    setIsFullscreen(false);
    // Remain in Focus Mode after exiting fullscreen
    setModeState((prev) => (prev === 'preview' ? 'focus' : prev === 'normal' ? 'focus' : prev));
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) {
      exitFullscreen();
    } else {
      enterFullscreen();
    }
  }, [isFullscreen, enterFullscreen, exitFullscreen]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName?.toLowerCase();
      const editing =
        tag === 'input' ||
        tag === 'textarea' ||
        tag === 'select' ||
        target?.isContentEditable;

      // Preview ESC: exit preview (handled here). Fullscreen ESC is owned by FocusWorkspace
      // so drawers can close first.
      if (event.key === 'Escape' && mode === 'preview' && !isFullscreen) {
        event.preventDefault();
        setMode('normal');
        return;
      }

      if (editing) return;
      if (!event.shiftKey || event.ctrlKey || event.metaKey || event.altKey) return;

      if (event.key === '!' || event.code === 'Digit1') {
        event.preventDefault();
        setIsFullscreen(false);
        setMode('normal');
      } else if (event.key === '@' || event.code === 'Digit2') {
        event.preventDefault();
        setMode('focus');
      } else if (event.key === '#' || event.code === 'Digit3') {
        event.preventDefault();
        setIsFullscreen(false);
        setMode('preview');
      }
    }

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [mode, setMode, isFullscreen]);

  /** QA / automation bridge — does not remount builders. */
  useEffect(() => {
    function onCmd(event: Event) {
      const detail = (event as CustomEvent<string>).detail;
      if (detail === 'enter') enterFullscreen();
      else if (detail === 'exit') exitFullscreen();
      else if (detail === 'toggle') {
        if (isFullscreen) exitFullscreen();
        else enterFullscreen();
      }
    }
    window.addEventListener('cs-fw-fullscreen', onCmd as EventListener);
    return () => window.removeEventListener('cs-fw-fullscreen', onCmd as EventListener);
  }, [enterFullscreen, exitFullscreen, isFullscreen]);

  return {
    mode,
    setMode,
    isPreview: mode === 'preview',
    isFocus: mode === 'focus',
    isNormal: mode === 'normal',
    isFullscreen,
    enterFullscreen,
    exitFullscreen,
    toggleFullscreen,
  };
}
