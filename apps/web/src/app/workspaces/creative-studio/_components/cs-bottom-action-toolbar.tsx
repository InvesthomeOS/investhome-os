'use client';

import {
  Fragment,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { useTranslations } from 'next-intl';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

export type CsBottomActionItem = {
  key: string;
  label: string;
  icon: IhIconName;
  onClick: () => void;
  testId?: string;
  disabled?: boolean;
  /** Low-priority items collapse into More first when space is tight. */
  priority?: 'high' | 'normal' | 'low';
};

export type CsBottomActionPrimary = {
  label: string;
  icon?: IhIconName;
  onClick: () => void;
  testId?: string;
  disabled?: boolean;
};

export type CsBottomActionToolbarProps = {
  /** Solid pill CTA. Omit for icon-only action rows (no large primary). */
  primary?: CsBottomActionPrimary | null;
  actions: CsBottomActionItem[];
  /** Optional custom node between primary and action grid (rare). */
  afterPrimary?: ReactNode;
  /**
   * Insert a vertical divider after this action key.
   * When set, action order is preserved (no priority re-sort).
   */
  dividerAfterKey?: string;
  /** Keep actions on one row; CSS shrinks spacing/labels before wrapping. */
  singleRow?: boolean;
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

function renderActionButton(
  action: CsBottomActionItem,
  onActivate: (action: CsBottomActionItem) => void,
) {
  return (
    <button
      type="button"
      className="cs-bat__action"
      data-testid={action.testId}
      title={action.label}
      disabled={action.disabled}
      aria-disabled={action.disabled || undefined}
      onClick={() => {
        if (action.disabled) return;
        onActivate(action);
      }}
    >
      <span className="cs-bat__action-icon" aria-hidden="true">
        <IhIcon name={action.icon} size={16} />
      </span>
      <span className="cs-bat__action-label">{action.label}</span>
    </button>
  );
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
  dividerAfterKey,
  singleRow = false,
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

  const preserveOrder = Boolean(dividerAfterKey) || singleRow;
  const ordered = preserveOrder ? actions : sortForCollapse(actions);
  const moreText = moreLabel ?? t('dock.more');
  const hasPrimary = Boolean(primary);

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
      const primaryW = hasPrimary ? (primaryRef.current?.offsetWidth ?? 120) : 0;
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
  }, [afterPrimary, hasPrimary, maxVisible, ordered.length]);

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
      className={['cs-bat__row', singleRow ? 'cs-bat__row--single' : null, className]
        .filter(Boolean)
        .join(' ')}
      data-testid={testId}
      role="group"
      aria-label={ariaLabel ?? t('dock.aria')}
    >
      {primary ? (
        <div className="cs-bat__primary" ref={primaryRef}>
          <button
            type="button"
            className="cs-bat__primary-btn"
            data-testid={primary.testId}
            disabled={primary.disabled}
            aria-disabled={primary.disabled || undefined}
            onClick={() => {
              if (primary.disabled) return;
              primary.onClick();
            }}
          >
            <IhIcon name={primary.icon ?? 'plus'} size={14} />
            <span>{primary.label}</span>
          </button>
        </div>
      ) : null}

      {afterPrimary}

      <div
        className={['cs-bat__actions', singleRow ? 'cs-bat__actions--single' : null]
          .filter(Boolean)
          .join(' ')}
        role="group"
      >
        {visible.map((action) => (
          <Fragment key={action.key}>
            {renderActionButton(action, (item) => item.onClick())}
            {dividerAfterKey && action.key === dividerAfterKey ? (
              <span className="cs-bat__divider" aria-hidden="true" data-testid={`${testId}-divider`} />
            ) : null}
          </Fragment>
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
                    disabled={action.disabled}
                    aria-disabled={action.disabled || undefined}
                    onClick={() => {
                      if (action.disabled) return;
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
