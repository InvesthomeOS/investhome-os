'use client';

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

export type SmbPostOverflowMenuItem = {
  key: string;
  label: string;
  destructive?: boolean;
  disabled?: boolean;
  testId?: string;
  onSelect: () => void;
};

export type SmbPostOverflowMenuProps = {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement | null>;
  items: SmbPostOverflowMenuItem[];
  onClose: () => void;
  ariaLabel: string;
};

const EDGE = 8;
const MENU_MIN_W = 148;

/**
 * Portal overflow menu for Gönderiler thumbnails.
 * Reuses SMB section-more / Projects DS menu language; flips near viewport edges.
 */
export function SmbPostOverflowMenu({
  open,
  anchorRef,
  items,
  onClose,
  ariaLabel,
}: SmbPostOverflowMenuProps) {
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
    const height = m.height || 44;

    let top = a.bottom + 4;
    let left = a.right - width;

    if (top + height > vh - EDGE) top = a.top - height - 4;
    if (top < EDGE) top = EDGE;
    if (left + width > vw - EDGE) left = vw - EDGE - width;
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
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('mousedown', onPointer, true);
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      window.removeEventListener('mousedown', onPointer, true);
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open, onClose, place, anchorRef]);

  if (!open || typeof document === 'undefined' || items.length === 0) return null;

  return createPortal(
    <div
      ref={menuRef}
      className="smb-ws__section-more smb-ws__section-more--portal"
      role="menu"
      aria-label={ariaLabel}
      data-testid="smb-post-overflow-menu"
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
          className={`smb-ws__section-more-item${item.destructive ? ' is-destructive' : ''}`}
          data-testid={item.testId}
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

export function SmbPostCardMore(props: {
  postId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  ariaLabel: string;
  items: SmbPostOverflowMenuItem[];
}) {
  const btnRef = useRef<HTMLButtonElement | null>(null);

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        className="smb-ws__page-more"
        aria-label={props.ariaLabel}
        aria-haspopup="menu"
        aria-expanded={props.open}
        data-testid={`smb-post-more-${props.postId}`}
        onPointerDown={(e) => {
          e.stopPropagation();
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
        }}
        onClick={(e) => {
          e.stopPropagation();
          e.preventDefault();
          props.onOpenChange(!props.open);
        }}
      >
        <span aria-hidden="true">⋯</span>
      </button>
      <SmbPostOverflowMenu
        open={props.open}
        anchorRef={btnRef}
        items={props.items}
        onClose={() => props.onOpenChange(false)}
        ariaLabel={props.ariaLabel}
      />
    </>
  );
}
