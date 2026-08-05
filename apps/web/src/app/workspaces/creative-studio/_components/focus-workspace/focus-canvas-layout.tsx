'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { FocusActionDock } from './focus-action-dock';
import { FocusSecondaryTray } from './focus-secondary-tray';
import { useFocusFsChrome } from './use-focus-fs-chrome';

export type FocusCanvasTraySlot = {
  label: string;
  count: number;
  /** Optional subtitle under label (e.g. "17 Page Sections"). */
  countLabel?: string;
  content: ReactNode;
  testId?: string;
  handleTestId?: string;
};

export type FocusCanvasDockSlot = {
  primary: ReactNode;
  secondary?: ReactNode;
  testId?: string;
  /** Applied in pinned/normal mode for builder-specific styling hooks */
  className?: string;
};

export type FocusCanvasLayoutProps = {
  isFullscreen: boolean;
  children: ReactNode;
  /** Compact top toolbar / center head */
  toolbar?: ReactNode;
  /** Extra chrome above stage (e.g. section tabs). Hidden in unpinned FS to maximize canvas. */
  aboveStage?: ReactNode;
  tray?: FocusCanvasTraySlot | null;
  dock?: FocusCanvasDockSlot | null;
  className?: string;
  stageClassName?: string;
  stageTestId?: string;
  /** Optional pin control rendered in toolbar area */
  showPinControl?: boolean;
  /** Keep structure tray + dock reserved in fullscreen (WB true-fullscreen). */
  keepBottomChrome?: boolean;
};

/**
 * Shared FS canvas hierarchy:
 * 1) compact toolbar  2) max-height stage  3) collapsible tray  4) optional action dock
 * Default FS: overlay tray + floating dock (canvas max height). Pin = permanently reserve space.
 */
export function FocusCanvasLayout({
  isFullscreen,
  children,
  toolbar,
  aboveStage,
  tray,
  dock,
  className,
  stageClassName,
  stageTestId = 'cs-fw-canvas-stage',
  showPinControl = true,
  keepBottomChrome = false,
}: FocusCanvasLayoutProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');
  const chrome = useFocusFsChrome({ isFullscreen, keepBottomChrome });

  const rootClass = [
    'cs-fw-fs-layout',
    isFullscreen ? 'cs-fw-fs-layout--fullscreen' : 'cs-fw-fs-layout--normal',
    chrome.pinBottomTools ? 'is-pin-bottom' : 'is-overlay-tools',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const hideAboveInFs = isFullscreen && !chrome.pinBottomTools;

  return (
    <div
      className={rootClass}
      data-testid="cs-fw-canvas-layout"
      data-fs-pin-bottom={chrome.pinBottomTools ? 'true' : 'false'}
      data-fs-tray-open={chrome.trayOpen ? 'true' : 'false'}
      onPointerMove={() => {
        if (isFullscreen && !chrome.pinBottomTools) chrome.revealDock();
      }}
    >
      {toolbar || showPinControl ? (
        <div className="cs-fw-fs__toolbar" data-testid="cs-fw-canvas-toolbar">
          {toolbar}
          {showPinControl && isFullscreen ? (
            <label className="cs-fw-fs__pin-bottom" data-testid="cs-fw-pin-bottom">
              <input
                type="checkbox"
                checked={chrome.pinBottomTools}
                onChange={(e) => chrome.setPinBottomTools(e.target.checked)}
              />
              <span>{t('pinBottomTools')}</span>
            </label>
          ) : null}
        </div>
      ) : null}

      {aboveStage && !hideAboveInFs ? (
        <div className="cs-fw-fs__above">{aboveStage}</div>
      ) : null}

      <div
        className={['cs-fw-fs__stage', stageClassName].filter(Boolean).join(' ')}
        data-testid={stageTestId}
      >
        {children}
      </div>

      {tray ? (
        <FocusSecondaryTray
          label={tray.label}
          count={tray.count}
          countLabel={tray.countLabel}
          open={chrome.toolsPinned ? true : chrome.trayOpen}
          pinned={chrome.toolsPinned}
          onToggle={chrome.toggleTray}
          onClose={() => chrome.setTrayOpen(false)}
          testId={tray.testId}
          handleTestId={tray.handleTestId}
        >
          {tray.content}
        </FocusSecondaryTray>
      ) : null}

      {dock ? (
        <FocusActionDock
          primary={dock.primary}
          secondary={dock.secondary}
          visible={chrome.toolsPinned || chrome.dockVisible}
          pinned={chrome.toolsPinned}
          overflowOpen={chrome.dockOverflowOpen}
          onOverflowOpenChange={chrome.setDockOverflowOpen}
          onPointerActivity={chrome.revealDock}
          testId={dock.testId}
          className={dock.className}
        />
      ) : null}
    </div>
  );
}
