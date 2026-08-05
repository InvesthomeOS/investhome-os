'use client';

import { useCallback, useEffect, useState } from 'react';

import {
  readPinBottomTools,
  registerFocusFsEscLayer,
  writePinBottomTools,
} from './focus-fs-chrome';

const DOCK_IDLE_MS = 2600;

export type UseFocusFsChromeOptions = {
  isFullscreen: boolean;
  /** When true, tray starts collapsed (default FS behavior). */
  defaultTrayCollapsed?: boolean;
  /**
   * Keep tray + dock permanently reserved in fullscreen (Figma-like).
   * Does not rewrite the shared pin-bottom preference.
   */
  keepBottomChrome?: boolean;
};

export type FocusFsChromeApi = {
  pinBottomTools: boolean;
  setPinBottomTools: (pinned: boolean) => void;
  togglePinBottomTools: () => void;
  trayOpen: boolean;
  setTrayOpen: (open: boolean) => void;
  toggleTray: () => void;
  dockOverflowOpen: boolean;
  setDockOverflowOpen: (open: boolean) => void;
  dockVisible: boolean;
  revealDock: () => void;
  /** True when tray+dock permanently reserve height (pin or non-FS). */
  toolsPinned: boolean;
};

/**
 * Fullscreen canvas chrome state: pin preference, collapsible tray, auto-hide dock.
 */
export function useFocusFsChrome({
  isFullscreen,
  defaultTrayCollapsed = true,
  keepBottomChrome = false,
}: UseFocusFsChromeOptions): FocusFsChromeApi {
  const [pinBottomTools, setPinState] = useState(false);
  const [trayOpen, setTrayOpen] = useState(!defaultTrayCollapsed || keepBottomChrome);
  const [dockOverflowOpen, setDockOverflowOpen] = useState(false);
  const [dockVisible, setDockVisible] = useState(true);

  useEffect(() => {
    setPinState(readPinBottomTools());
  }, []);

  useEffect(() => {
    if (!isFullscreen) {
      setTrayOpen(true);
      setDockOverflowOpen(false);
      setDockVisible(true);
      return;
    }
    // Enter FS: collapse tray by default unless pinned / keepBottomChrome
    if (keepBottomChrome || readPinBottomTools()) {
      setTrayOpen(true);
    } else {
      setTrayOpen(false);
    }
    setDockOverflowOpen(false);
    setDockVisible(true);
  }, [isFullscreen, keepBottomChrome]);

  const setPinBottomTools = useCallback((pinned: boolean) => {
    setPinState(pinned);
    writePinBottomTools(pinned);
    if (pinned || keepBottomChrome) {
      setTrayOpen(true);
      setDockVisible(true);
    } else if (isFullscreen) {
      setTrayOpen(false);
    }
  }, [isFullscreen, keepBottomChrome]);

  const togglePinBottomTools = useCallback(() => {
    setPinBottomTools(!pinBottomTools);
  }, [pinBottomTools, setPinBottomTools]);

  const toggleTray = useCallback(() => {
    setTrayOpen((prev) => !prev);
  }, []);

  const revealDock = useCallback(() => {
    setDockVisible(true);
  }, []);

  const toolsPinned = !isFullscreen || pinBottomTools || keepBottomChrome;

  // Auto-hide floating dock after inactivity (unpinned FS only)
  useEffect(() => {
    if (!isFullscreen || pinBottomTools || keepBottomChrome || dockOverflowOpen) {
      setDockVisible(true);
      return;
    }
    let timer: ReturnType<typeof setTimeout> | null = null;
    function scheduleHide() {
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => setDockVisible(false), DOCK_IDLE_MS);
    }
    scheduleHide();
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isFullscreen, pinBottomTools, keepBottomChrome, dockOverflowOpen, trayOpen]);

  // ESC layers: tray → dock overflow
  useEffect(() => {
    if (!isFullscreen) return;
    const unsubTray = registerFocusFsEscLayer({
      id: 'tray',
      priority: 40,
      isActive: () => trayOpen && !pinBottomTools && !keepBottomChrome,
      close: () => setTrayOpen(false),
    });
    const unsubDock = registerFocusFsEscLayer({
      id: 'dockOverflow',
      priority: 30,
      isActive: () => dockOverflowOpen,
      close: () => setDockOverflowOpen(false),
    });
    return () => {
      unsubTray();
      unsubDock();
    };
  }, [isFullscreen, trayOpen, pinBottomTools, keepBottomChrome, dockOverflowOpen]);

  return {
    pinBottomTools,
    setPinBottomTools,
    togglePinBottomTools,
    trayOpen,
    setTrayOpen,
    toggleTray,
    dockOverflowOpen,
    setDockOverflowOpen,
    dockVisible,
    revealDock,
    toolsPinned,
  };
}
