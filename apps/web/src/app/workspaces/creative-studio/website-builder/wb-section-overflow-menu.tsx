'use client';

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { createPortal } from 'react-dom';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';

export type WbOverflowMenuItem = {
  key: string;
  label: string;
  destructive?: boolean;
  disabled?: boolean;
  onSelect: () => void;
};

export type WbSectionOverflowMenuProps = {
  open: boolean;
  anchorRef: React.RefObject<HTMLElement | null>;
  items: WbOverflowMenuItem[];
  onClose: () => void;
  ariaLabel: string;
};

const EDGE = 10;
const MENU_MIN_W = 210;

/**
 * Portal-based section overflow menu for Website Builder.
 * Flips up/left near viewport edges so fullscreen canvas overflow never clips it.
 */
export function WbSectionOverflowMenu({
  open,
  anchorRef,
  items,
  onClose,
  ariaLabel,
}: WbSectionOverflowMenuProps) {
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
      className="wb-ws__section-more wb-ws__section-more--portal"
      role="menu"
      aria-label={ariaLabel}
      data-testid="wb-section-overflow-menu"
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
          className={`wb-ws__section-more-item${item.destructive ? ' is-destructive' : ''}`}
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

export type WbSectionToolbarProps = {
  sectionId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onEdit: () => void;
  onAdd: () => void;
  onAi: () => void;
  moreItems: WbOverflowMenuItem[];
  labels: {
    edit: string;
    add: string;
    ai: string;
    more: string;
  };
  variant?: 'default' | 'hero';
};

/** Consistent section chrome: Edit / Add / AI / More (portal menu). */
export function WbSectionToolbar({
  sectionId,
  open,
  onOpenChange,
  onEdit,
  onAdd,
  onAi,
  moreItems,
  labels,
  variant = 'default',
}: WbSectionToolbarProps) {
  const moreBtnRef = useRef<HTMLButtonElement | null>(null);

  const iconBtn = (name: IhIconName, title: string, onClick: () => void, active?: boolean) => (
    <button
      type="button"
      className={`wb-ws__icon-btn${active ? ' is-active' : ''}`}
      title={title}
      aria-label={title}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
    >
      <IhIcon name={name} size={14} aria-hidden />
    </button>
  );

  return (
    <div
      className={`wb-ws__section-toolbar${variant === 'hero' ? ' wb-ws__section-toolbar--hero' : ''}`}
      data-testid={`wb-section-toolbar-${sectionId}`}
      role="toolbar"
      aria-label="Section actions"
    >
      {iconBtn('design', labels.edit, onEdit)}
      {iconBtn('plus', labels.add, onAdd)}
      {iconBtn('sparkles', labels.ai, onAi)}
      <button
        ref={moreBtnRef}
        type="button"
        className={`wb-ws__icon-btn${open ? ' is-active' : ''}`}
        title={labels.more}
        aria-label={labels.more}
        aria-expanded={open}
        aria-haspopup="menu"
        data-testid={`wb-section-more-${sectionId}`}
        onClick={(e) => {
          e.stopPropagation();
          onOpenChange(!open);
        }}
      >
        <span aria-hidden="true" className="wb-ws__more-glyph">
          ⋯
        </span>
      </button>
      <WbSectionOverflowMenu
        open={open}
        anchorRef={moreBtnRef}
        items={moreItems}
        onClose={() => onOpenChange(false)}
        ariaLabel={labels.more}
      />
    </div>
  );
}
