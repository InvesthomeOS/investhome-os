'use client';

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  CS_FOCUS_LEFT_RAIL,
  CS_FOCUS_RIGHT_RAIL,
  type CreativeStudioWorkspaceMode,
  type FocusRailItem,
  type FocusRailSide,
} from './creative-studio-focus-types';
import { tryCloseFocusFsEscLayer } from './focus-fs-chrome';

import './creative-studio-focus-workspace.css';

const HOVER_OPEN_MS = 140;
const LEAVE_CLOSE_MS = 220;

export type CreativeStudioFocusWorkspaceProps = {
  mode: CreativeStudioWorkspaceMode;
  onModeChange: (mode: CreativeStudioWorkspaceMode) => void;
  left: ReactNode;
  center: ReactNode;
  right: ReactNode;
  layoutClassName: string;
  leftRail?: FocusRailItem[];
  rightRail?: FocusRailItem[];
  onLeftRailSelect?: (id: string) => void;
  onRightRailSelect?: (id: string) => void;
  className?: string;
  /** Fullscreen Focus shell — Focus Mode using full viewport; rails remain visible. */
  isFullscreen?: boolean;
  onExitFullscreen?: () => void;
};

type DrawerSideState = {
  activeId: string | null;
  open: boolean;
  pinned: boolean;
};

const INITIAL_DRAWER: DrawerSideState = {
  activeId: null,
  open: false,
  pinned: false,
};

type FocusRailProps = {
  side: FocusRailSide;
  items: FocusRailItem[];
  activeId: string | null;
  pinned: boolean;
  onActivate: (id: string) => void;
  onHoverStart: (id: string) => void;
  onHoverEnd: () => void;
};

function FocusRail({
  side,
  items,
  activeId,
  pinned,
  onActivate,
  onHoverStart,
  onHoverEnd,
}: FocusRailProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');

  return (
    <nav
      className={`cs-fw__rail cs-fw__rail--${side}`}
      data-testid={`cs-fw-rail-${side}`}
      aria-label={t(`rails.${side}Aria`)}
      onMouseLeave={onHoverEnd}
    >
      {items.map((item) => {
        const isActive = activeId === item.id;
        return (
          <button
            key={item.id}
            type="button"
            className={[
              'cs-fw__rail-btn',
              isActive ? 'is-active' : '',
              isActive && pinned ? 'is-pinned' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            data-testid={`cs-fw-rail-${side}-${item.id}`}
            title={item.label ?? t(`rails.${item.labelKey}`)}
            aria-label={item.label ?? t(`rails.${item.labelKey}`)}
            aria-pressed={isActive}
            onClick={() => onActivate(item.id)}
            onMouseEnter={() => onHoverStart(item.id)}
          >
            <IhIcon name={item.icon} size={16} />
          </button>
        );
      })}
    </nav>
  );
}

export function CreativeStudioFocusWorkspace({
  mode,
  onModeChange,
  left,
  center,
  right,
  layoutClassName,
  leftRail = CS_FOCUS_LEFT_RAIL,
  rightRail = CS_FOCUS_RIGHT_RAIL,
  onLeftRailSelect,
  onRightRailSelect,
  className,
  isFullscreen = false,
  onExitFullscreen,
}: CreativeStudioFocusWorkspaceProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');
  const rootRef = useRef<HTMLDivElement | null>(null);
  /** True only after Fullscreen API successfully activates on our shell. */
  const browserFsActiveRef = useRef(false);

  const [leftDrawer, setLeftDrawer] = useState<DrawerSideState>(INITIAL_DRAWER);
  const [rightDrawer, setRightDrawer] = useState<DrawerSideState>(INITIAL_DRAWER);

  const leftOpenTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leftCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rightOpenTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rightCloseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback((ref: { current: ReturnType<typeof setTimeout> | null }) => {
    if (ref.current != null) {
      clearTimeout(ref.current);
      ref.current = null;
    }
  }, []);

  const clearSideTimers = useCallback(
    (side: FocusRailSide) => {
      if (side === 'left') {
        clearTimer(leftOpenTimer);
        clearTimer(leftCloseTimer);
      } else {
        clearTimer(rightOpenTimer);
        clearTimer(rightCloseTimer);
      }
    },
    [clearTimer],
  );

  const resetDrawers = useCallback(() => {
    clearSideTimers('left');
    clearSideTimers('right');
    setLeftDrawer(INITIAL_DRAWER);
    setRightDrawer(INITIAL_DRAWER);
  }, [clearSideTimers]);

  useEffect(() => {
    if (mode !== 'focus') {
      resetDrawers();
    }
  }, [mode, resetDrawers]);

  useEffect(() => {
    return () => {
      clearSideTimers('left');
      clearSideTimers('right');
    };
  }, [clearSideTimers]);

  /** Browser Fullscreen API on the shared focus shell (rails included). CSS shell is the source of truth. */
  useEffect(() => {
    const el = rootRef.current;
    if (!el) return;

    if (isFullscreen) {
      if (!document.fullscreenElement && typeof el.requestFullscreen === 'function') {
        void el
          .requestFullscreen()
          .then(() => {
            browserFsActiveRef.current = true;
          })
          .catch(() => {
            // NotAllowedError / headless — keep CSS fullscreen shell
            browserFsActiveRef.current = false;
          });
      }
      return;
    }

    browserFsActiveRef.current = false;
    if (document.fullscreenElement === el) {
      void document.exitFullscreen().catch(() => undefined);
    }
  }, [isFullscreen]);

  useEffect(() => {
    function onFsChange() {
      const el = rootRef.current;
      if (document.fullscreenElement === el) {
        browserFsActiveRef.current = true;
        return;
      }
      // Only mirror browser exit into React state if API fullscreen was actually active.
      // Failed/instant-denied requests must not clear CSS fullscreen Focus shell.
      if (!document.fullscreenElement && browserFsActiveRef.current && isFullscreen) {
        browserFsActiveRef.current = false;
        onExitFullscreen?.();
      }
    }
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, [isFullscreen, onExitFullscreen]);

  /**
   * ESC in Focus / Fullscreen Focus:
   * 1) close unpinned drawer
   * 2) close bottom tray
   * 3) close action dock overflow
   * 4) else exit fullscreen (remain Focus Mode)
   * Preview ESC is handled by the focus-mode hook.
   */
  useEffect(() => {
    if (mode !== 'focus' && !isFullscreen) return;

    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape') return;

      let closedDrawer = false;
      setLeftDrawer((prev) => {
        if (prev.open && !prev.pinned) {
          closedDrawer = true;
          return INITIAL_DRAWER;
        }
        return prev;
      });
      setRightDrawer((prev) => {
        if (prev.open && !prev.pinned) {
          closedDrawer = true;
          return INITIAL_DRAWER;
        }
        return prev;
      });

      if (closedDrawer) {
        event.preventDefault();
        event.stopPropagation();
        clearSideTimers('left');
        clearSideTimers('right');
        return;
      }

      if (isFullscreen && tryCloseFocusFsEscLayer()) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }

      if (isFullscreen) {
        event.preventDefault();
        event.stopPropagation();
        onExitFullscreen?.();
      }
    }

    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [mode, isFullscreen, clearSideTimers, onExitFullscreen]);

  const activateRail = useCallback(
    (side: FocusRailSide, id: string) => {
      clearSideTimers(side);
      const setDrawer = side === 'left' ? setLeftDrawer : setRightDrawer;
      const onSelect = side === 'left' ? onLeftRailSelect : onRightRailSelect;

      setDrawer((prev) => {
        if (prev.activeId !== id || !prev.open) {
          onSelect?.(id);
          return { activeId: id, open: true, pinned: false };
        }
        if (!prev.pinned) {
          onSelect?.(id);
          return { ...prev, pinned: true };
        }
        onSelect?.(id);
        return INITIAL_DRAWER;
      });
    },
    [clearSideTimers, onLeftRailSelect, onRightRailSelect],
  );

  const hoverStart = useCallback(
    (side: FocusRailSide, id: string) => {
      if (mode !== 'focus' && !isFullscreen) return;
      const openRef = side === 'left' ? leftOpenTimer : rightOpenTimer;
      const closeRef = side === 'left' ? leftCloseTimer : rightCloseTimer;
      const setDrawer = side === 'left' ? setLeftDrawer : setRightDrawer;
      const onSelect = side === 'left' ? onLeftRailSelect : onRightRailSelect;

      clearTimer(closeRef);

      setDrawer((prev) => {
        if (prev.pinned) return prev;
        clearTimer(openRef);
        openRef.current = setTimeout(() => {
          setDrawer({ activeId: id, open: true, pinned: false });
          onSelect?.(id);
        }, HOVER_OPEN_MS);
        return prev;
      });
    },
    [mode, isFullscreen, clearTimer, onLeftRailSelect, onRightRailSelect],
  );

  const hoverEnd = useCallback(
    (side: FocusRailSide) => {
      if (mode !== 'focus' && !isFullscreen) return;
      const openRef = side === 'left' ? leftOpenTimer : rightOpenTimer;
      const closeRef = side === 'left' ? leftCloseTimer : rightCloseTimer;
      const setDrawer = side === 'left' ? setLeftDrawer : setRightDrawer;

      clearTimer(openRef);
      setDrawer((prev) => {
        if (prev.pinned || !prev.open) return prev;
        clearTimer(closeRef);
        closeRef.current = setTimeout(() => {
          setDrawer(INITIAL_DRAWER);
        }, LEAVE_CLOSE_MS);
        return prev;
      });
    },
    [mode, isFullscreen, clearTimer],
  );

  const keepDrawerOpen = useCallback(
    (side: FocusRailSide) => {
      clearSideTimers(side);
    },
    [clearSideTimers],
  );

  const pinToggle = useCallback((side: FocusRailSide) => {
    const setDrawer = side === 'left' ? setLeftDrawer : setRightDrawer;
    setDrawer((prev) => {
      if (!prev.open || !prev.activeId) return prev;
      if (prev.pinned) {
        return INITIAL_DRAWER;
      }
      return { ...prev, pinned: true };
    });
  }, []);

  const closeDrawer = useCallback(
    (side: FocusRailSide) => {
      clearSideTimers(side);
      if (side === 'left') setLeftDrawer(INITIAL_DRAWER);
      else setRightDrawer(INITIAL_DRAWER);
    },
    [clearSideTimers],
  );

  const leftItem = leftRail.find((i) => i.id === leftDrawer.activeId);
  const rightItem = rightRail.find((i) => i.id === rightDrawer.activeId);

  // Fullscreen always renders Focus chrome (rails) even if mode briefly lags
  const effectiveMode: CreativeStudioWorkspaceMode =
    isFullscreen && mode !== 'focus' ? 'focus' : mode;

  const rootClass = [
    'cs-fw',
    `cs-fw--${effectiveMode}`,
    isFullscreen ? 'cs-fw--fullscreen' : '',
    layoutClassName,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const renderDrawer = (
    side: FocusRailSide,
    drawer: DrawerSideState,
    content: ReactNode,
    item: FocusRailItem | undefined,
  ) => {
    const open = drawer.open && Boolean(drawer.activeId);
    return (
      <aside
        className={[
          'cs-fw__panel-slot',
          `cs-fw__panel-slot--${side}`,
          'is-drawer',
          open ? 'is-open' : '',
          drawer.pinned ? 'is-pinned' : '',
        ]
          .filter(Boolean)
          .join(' ')}
        data-testid={`cs-fw-drawer-${side}`}
        onMouseEnter={() => keepDrawerOpen(side)}
        onMouseLeave={() => hoverEnd(side)}
        aria-hidden={!open}
      >
        <div className="cs-fw__drawer-chrome">
          <span className="cs-fw__drawer-title">
            {item ? item.label ?? t(`rails.${item.labelKey}`) : t(`rails.${side}`)}
          </span>
          <div className="cs-fw__drawer-actions">
            <button
              type="button"
              className={['cs-fw__pin', drawer.pinned ? 'is-active' : '']
                .filter(Boolean)
                .join(' ')}
              data-testid={`cs-fw-pin-${side}`}
              onClick={() => pinToggle(side)}
            >
              <IhIcon name={drawer.pinned ? 'check' : 'target'} size={12} />
              {drawer.pinned ? t('unpin') : t('pin')}
            </button>
            <button
              type="button"
              className="cs-fw__drawer-close"
              data-testid={`cs-fw-close-${side}`}
              aria-label={t('closeDrawer')}
              onClick={() => closeDrawer(side)}
            >
              <span aria-hidden="true">X</span>
            </button>
          </div>
        </div>
        <div className="cs-fw__panel-body">{content}</div>
      </aside>
    );
  };

  return (
    <div
      ref={rootRef}
      className={rootClass}
      data-cs-focus-mode={effectiveMode}
      data-cs-fullscreen={isFullscreen ? 'true' : 'false'}
      data-testid="cs-fw-workspace"
      style={{ ['--cs-fw-drawer-ms' as string]: '200ms' }}
    >
      {effectiveMode === 'normal' && (
        <>
          <div className="cs-fw__panel-slot cs-fw__panel-slot--left is-docked" data-testid="cs-fw-left-slot">
            <div className="cs-fw__panel-body">{left}</div>
          </div>
          <div className="cs-fw__panel-slot cs-fw__panel-slot--center" data-testid="cs-fw-center-slot">
            <div className="cs-fw__panel-body">{center}</div>
          </div>
          <div className="cs-fw__panel-slot cs-fw__panel-slot--right is-docked" data-testid="cs-fw-right-slot">
            <div className="cs-fw__panel-body">{right}</div>
          </div>
        </>
      )}

      {effectiveMode === 'focus' && (
        <>
          <FocusRail
            side="left"
            items={leftRail}
            activeId={leftDrawer.activeId}
            pinned={leftDrawer.pinned}
            onActivate={(id) => activateRail('left', id)}
            onHoverStart={(id) => hoverStart('left', id)}
            onHoverEnd={() => hoverEnd('left')}
          />
          <div className="cs-fw__panel-slot cs-fw__panel-slot--center" data-testid="cs-fw-center-slot">
            {center}
          </div>
          <FocusRail
            side="right"
            items={rightRail}
            activeId={rightDrawer.activeId}
            pinned={rightDrawer.pinned}
            onActivate={(id) => activateRail('right', id)}
            onHoverStart={(id) => hoverStart('right', id)}
            onHoverEnd={() => hoverEnd('right')}
          />
          {renderDrawer('left', leftDrawer, left, leftItem)}
          {renderDrawer('right', rightDrawer, right, rightItem)}
          {isFullscreen ? (
            <div className="cs-fw__fullscreen-bar" data-testid="cs-fw-fullscreen-bar">
              <span className="cs-fw__fullscreen-hint">{t('fullscreenEscHint')}</span>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                data-testid="cs-fw-exit-fullscreen"
                onClick={() => onExitFullscreen?.()}
              >
                {t('exitFullscreen')}
              </Button>
            </div>
          ) : null}
        </>
      )}

      {effectiveMode === 'preview' && (
        <>
          <div className="cs-fw__panel-slot cs-fw__panel-slot--center" data-testid="cs-fw-center-slot">
            {center}
          </div>
          <div className="cs-fw__preview-bar" data-testid="cs-fw-preview-bar">
            <span className="cs-fw__preview-hint">{t('previewEscHint')}</span>
            <Button
              type="button"
              size="sm"
              variant="secondary"
              data-testid="cs-fw-exit-preview"
              onClick={() => onModeChange('normal')}
            >
              {t('exitPreview')}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
