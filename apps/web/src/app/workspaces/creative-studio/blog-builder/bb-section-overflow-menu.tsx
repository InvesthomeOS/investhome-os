'use client';

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { createPortal } from 'react-dom';

export type BbOverflowMenuItem = {
  key: string;
  label: string;
  destructive?: boolean;
  disabled?: boolean;
  onSelect: () => void;
};

export type BbSectionOverflowMenuProps = {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement | null>;
  items: BbOverflowMenuItem[];
  onClose: () => void;
  ariaLabel: string;
};

const EDGE = 10;
const MENU_MIN_W = 210;

/**
 * Portal-based section overflow menu (blog-builder local).
 * Flips up/left near viewport edges so canvas overflow never clips it.
 */
export function BbSectionOverflowMenu({
  open,
  anchorRef,
  items,
  onClose,
  ariaLabel,
}: BbSectionOverflowMenuProps) {
  const menuRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const [ready, setReady] = useState(false);

  const place = useCallback(() => {
    const anchor = anchorRef.current;
    const menu = menuRef.current;
    if (!anchor || !menu) return;

    const a = anchor.getBoundingClientRect();
    const m = menu.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const width = Math.max(MENU_MIN_W, m.width || MENU_MIN_W);
    const height = m.height || 200;

    let top = a.bottom + 6;
    let left = a.right - width;

    if (top + height > vh - EDGE) {
      top = a.top - height - 6;
    }
    if (top < EDGE) top = EDGE;

    if (left + width > vw - EDGE) {
      left = vw - EDGE - width;
    }
    if (left < EDGE) left = EDGE;

    setPos({ top, left });
    setReady(true);
  }, [anchorRef]);

  useLayoutEffect(() => {
    if (!open) {
      setReady(false);
      return;
    }
    place();
  }, [open, place, items.length]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    }
    function onPointer(e: MouseEvent) {
      const t = e.target as Node;
      if (menuRef.current?.contains(t)) return;
      if (anchorRef.current?.contains(t)) return;
      onClose();
    }
    function onReposition() {
      place();
    }
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('mousedown', onPointer, true);
    window.addEventListener('resize', onReposition);
    window.addEventListener('scroll', onReposition, true);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      window.removeEventListener('mousedown', onPointer, true);
      window.removeEventListener('resize', onReposition);
      window.removeEventListener('scroll', onReposition, true);
    };
  }, [open, onClose, place, anchorRef]);

  if (!open || typeof document === 'undefined' || items.length === 0) return null;

  return createPortal(
    <div
      ref={menuRef}
      className="bb-ws__section-more bb-ws__section-more--portal"
      role="menu"
      aria-label={ariaLabel}
      data-testid="bb-section-overflow-menu"
      style={{
        position: 'fixed',
        top: pos.top,
        left: pos.left,
        visibility: ready ? 'visible' : 'hidden',
        zIndex: 1200,
      }}
    >
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          role="menuitem"
          disabled={item.disabled}
          aria-disabled={item.disabled || undefined}
          className={`bb-ws__section-more-item${item.destructive ? ' is-destructive' : ''}`}
          onClick={() => {
            if (item.disabled) return;
            item.onSelect();
            onClose();
          }}
        >
          {item.label}
        </button>
      ))}
    </div>,
    document.body,
  );
}
