'use client';

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

export type CsBottomActionItem = {
  key: string;
  label: string;
  icon: IhIconName;
  onClick: () => void;
  testId?: string;
  /** Low-priority items collapse into More first when space is tight. */
  priority?: 'high' | 'normal' | 'low';
};

export type CsBottomActionPrimary = {
  label: string;
  icon?: IhIconName;
  onClick: () => void;
  testId?: string;
};

export type CsBottomActionToolbarProps = {
  primary: CsBottomActionPrimary;
  actions: CsBottomActionItem[];
  /** Optional custom node between primary and action grid (rare). */
  afterPrimary?: ReactNode;
  ariaLabel?: string;
  moreLabel?: string;
  className?: string;
  testId?: string;
  /**
   * Cap visible secondary actions (rest go to More).
   * When omitted, visibility is computed from available width.
   */
  maxVisible?: number;
};

const ITEM_MIN_PX = 54;
const MORE_MIN_PX = 54;
const GAP_PX = 5;

function sortForCollapse(actions: CsBottomActionItem[]): CsBottomActionItem[] {
  const rank = { high: 0, normal: 1, low: 2 } as const;
  return [...actions].sort((a, b) => (rank[a.priority ?? 'normal'] - rank[b.priority ?? 'normal']));
}

/**
 * Shared Creative Studio bottom action row content:
 * solid light primary pill + icon-above-label ghost tools + overflow More.
 * Visual chrome (dark teal ribbon) comes from FocusActionDock / `.cs-fw-dock.cs-bat`.
 * WB polish is the global default — do not recolor per builder.
 */
export function CsBottomActionToolbar({
  primary,
  actions,
  afterPrimary,
  ariaLabel,
  moreLabel,
  className,
  testId = 'cs-bat',
  maxVisible,
}: CsBottomActionToolbarProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');
  const rootRef = useRef<HTMLDivElement | null>(null);
  const primaryRef = useRef<HTMLDivElement | null>(null);
  const [overflowOpen, setOverflowOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(() =>
    typeof maxVisible === 'number' ? maxVisible : actions.length,
  );

  const ordered = sortForCollapse(actions);
  const moreText = moreLabel ?? t('dock.more');

  useLayoutEffect(() => {
    if (typeof maxVisible === 'number') {
      setVisibleCount(Math.max(0, Math.min(maxVisible, ordered.length)));
      return;
    }

    const root = rootRef.current;
    if (!root) return;

    function measure() {
      const el = rootRef.current;
      if (!el) return;
      const primaryW = primaryRef.current?.offsetWidth ?? 120;
      const afterW = afterPrimary ? 48 : 0;
      const available = Math.max(0, el.clientWidth - primaryW - afterW - GAP_PX * 3 - 8);
      const canFitWithMore = Math.max(0, Math.floor((available - MORE_MIN_PX - GAP_PX) / (ITEM_MIN_PX + GAP_PX)));
      const canFitAll = Math.floor(available / (ITEM_MIN_PX + GAP_PX));
      if (canFitAll >= ordered.length) {
        setVisibleCount(ordered.length);
        return;
      }
      setVisibleCount(Math.min(ordered.length, Math.max(0, canFitWithMore)));
    }

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(root);
    return () => ro.disconnect();
  }, [afterPrimary, maxVisible, ordered.length]);

  useEffect(() => {
    if (!overflowOpen) return;
    function onDoc(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOverflowOpen(false);
      }
    }
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [overflowOpen]);

  const visible = ordered.slice(0, visibleCount);
  const overflow = ordered.slice(visibleCount);
  const hasOverflow = overflow.length > 0;

  return (
    <div
      ref={rootRef}
      className={['cs-bat__row', className].filter(Boolean).join(' ')}
      data-testid={testId}
      role="group"
      aria-label={ariaLabel ?? t('dock.aria')}
    >
      <div className="cs-bat__primary" ref={primaryRef}>
        <button
          type="button"
          className="cs-bat__primary-btn"
          data-testid={primary.testId}
          onClick={primary.onClick}
        >
          <IhIcon name={primary.icon ?? 'plus'} size={14} />
          <span>{primary.label}</span>
        </button>
      </div>

      {afterPrimary}

      <div className="cs-bat__actions" role="group">
        {visible.map((action) => (
          <button
            key={action.key}
            type="button"
            className="cs-bat__action"
            data-testid={action.testId}
            title={action.label}
            onClick={action.onClick}
          >
            <span className="cs-bat__action-icon" aria-hidden="true">
              <IhIcon name={action.icon} size={16} />
            </span>
            <span className="cs-bat__action-label">{action.label}</span>
          </button>
        ))}

        {hasOverflow ? (
          <div className="cs-bat__more-wrap">
            <button
              type="button"
              className="cs-bat__action cs-bat__more-btn"
              data-testid={`${testId}-more`}
              aria-expanded={overflowOpen}
              aria-haspopup="menu"
              title={moreText}
              onClick={() => setOverflowOpen((open) => !open)}
            >
              <span className="cs-bat__action-icon" aria-hidden="true">
                <IhIcon name="chevronDown" size={16} />
              </span>
              <span className="cs-bat__action-label">{moreText}</span>
            </button>
            {overflowOpen ? (
              <div className="cs-bat__overflow" data-testid={`${testId}-overflow`} role="menu">
                {overflow.map((action) => (
                  <button
                    key={action.key}
                    type="button"
                    role="menuitem"
                    className="cs-bat__overflow-item"
                    data-testid={action.testId}
                    onClick={() => {
                      setOverflowOpen(false);
                      action.onClick();
                    }}
                  >
                    <IhIcon name={action.icon} size={14} />
                    <span>{action.label}</span>
                  </button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
