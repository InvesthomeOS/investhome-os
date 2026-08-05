'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

export type FocusActionDockProps = {
  primary: ReactNode;
  secondary?: ReactNode;
  visible: boolean;
  pinned: boolean;
  overflowOpen: boolean;
  onOverflowOpenChange: (open: boolean) => void;
  onPointerActivity?: () => void;
  testId?: string;
  className?: string;
};

/**
 * Compact bottom action dock. Unpinned FS: floats, auto-hides, primary + More.
 * Pinned / normal: in-flow toolbar with all actions.
 */
export function FocusActionDock({
  primary,
  secondary,
  visible,
  pinned,
  overflowOpen,
  onOverflowOpenChange,
  onPointerActivity,
  testId = 'cs-fw-dock',
  className,
}: FocusActionDockProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');
  const rootRef = useRef<HTMLDivElement | null>(null);
  const hasSecondary = Boolean(secondary);

  useEffect(() => {
    if (!overflowOpen) return;
    function onDoc(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        onOverflowOpenChange(false);
      }
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [overflowOpen, onOverflowOpenChange]);

  if (pinned) {
    return (
      <div
        ref={rootRef}
        className={['cs-fw-dock', 'cs-fw-dock--pinned', 'cs-bat', className]
          .filter(Boolean)
          .join(' ')}
        data-testid={testId}
        data-visible="true"
        role="toolbar"
        aria-label={t('dock.aria')}
        onPointerMove={onPointerActivity}
        onFocusCapture={onPointerActivity}
      >
        <div className="cs-fw-dock__primary">{primary}</div>
        {hasSecondary ? <div className="cs-fw-dock__secondary">{secondary}</div> : null}
      </div>
    );
  }

  return (
    <div
      ref={rootRef}
      className={[
        'cs-fw-dock',
        'cs-fw-dock--float',
        'cs-bat',
        visible ? 'is-visible' : 'is-hidden',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      data-testid={testId}
      data-visible={visible ? 'true' : 'false'}
      role="toolbar"
      aria-label={t('dock.aria')}
      onPointerMove={onPointerActivity}
      onFocusCapture={() => {
        onPointerActivity?.();
      }}
    >
      <div className="cs-fw-dock__primary">{primary}</div>
      {hasSecondary ? (
        <div className="cs-fw-dock__more-wrap">
          <Button
            type="button"
            size="sm"
            variant="secondary"
            data-testid={`${testId}-more`}
            aria-expanded={overflowOpen}
            onClick={() => onOverflowOpenChange(!overflowOpen)}
          >
            {t('dock.more')}
          </Button>
          {overflowOpen ? (
            <div className="cs-fw-dock__overflow" data-testid={`${testId}-overflow`} role="menu">
              {secondary}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
