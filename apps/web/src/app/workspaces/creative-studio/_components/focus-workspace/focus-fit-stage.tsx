'use client';

import type { ReactNode } from 'react';

import type { FitToViewEngineApi } from './use-fit-to-view-engine';

export type FocusFitStageProps = {
  engine: FitToViewEngineApi;
  children: ReactNode;
  className?: string;
  /** Optional override test id for the artboard frame. */
  artboardTestId?: string;
  /**
   * When true (default), artboard is sized to engine.stageSize and children fill it.
   * When false, children keep intrinsic size and are transform-scaled (design-pixel mode).
   */
  sizeArtboard?: boolean;
  /** Intrinsic design size — required when sizeArtboard is false. */
  contentWidth?: number;
  contentHeight?: number;
};

/**
 * Shared Fit-To-View viewport: grey workspace, pan/zoom handlers, centered artboard.
 * Artwork mode never crops — Fit keeps the entire frame inside the stage bbox.
 * Document mode uses a readable width column with vertical scroll.
 */
export function FocusFitStage({
  engine,
  children,
  className,
  artboardTestId = 'cs-ftv-artboard',
  sizeArtboard = true,
  contentWidth,
  contentHeight,
}: FocusFitStageProps) {
  const { viewportProps, pan, spacePanActive, stageSize, mode, canvasType } = engine;

  const rootClass = [
    'cs-ftv-viewport',
    spacePanActive ? 'is-space-pan' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const artboardStyle = sizeArtboard
    ? {
        width: Math.round(stageSize.width),
        height: Math.round(stageSize.height),
        transform: `translate(${pan.x}px, ${pan.y}px)`,
      }
    : {
        width: contentWidth ?? stageSize.width / Math.max(0.001, stageSize.scale),
        height: contentHeight ?? stageSize.height / Math.max(0.001, stageSize.scale),
        transform: `translate(${pan.x}px, ${pan.y}px) scale(${stageSize.scale})`,
        transformOrigin: 'center center',
      };

  return (
    <div
      {...viewportProps}
      className={rootClass}
      data-ftv-size-mode={sizeArtboard ? 'stage' : 'scale'}
      data-ftv-canvas={canvasType}
    >
      <div className="cs-ftv-workspace" data-testid="cs-ftv-workspace">
        <div
          className="cs-ftv-artboard"
          data-testid={artboardTestId}
          data-ftv-mode={mode}
          data-ftv-canvas={canvasType}
          style={artboardStyle}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
