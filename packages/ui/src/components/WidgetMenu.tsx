'use client';

import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

import { IconButton } from './IconButton.js';

export interface WidgetMenuItem {
  id: string;
  label: string;
  onSelect: () => void;
  disabled?: boolean;
}

export interface WidgetMenuProps {
  items: WidgetMenuItem[];
  triggerLabel: string;
  triggerIcon?: ReactNode;
  className?: string;
}

export function WidgetMenu({ items, triggerLabel, triggerIcon, className }: WidgetMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onPointer);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onPointer);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className={`ds-widget-menu${className ? ` ${className}` : ''}`} ref={rootRef}>
      <IconButton
        label={triggerLabel}
        variant="ghost"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        onClick={() => setOpen((value) => !value)}
      >
        {triggerIcon ?? (
          <span aria-hidden="true" style={{ fontSize: '1.1rem', lineHeight: 1 }}>
            ⋯
          </span>
        )}
      </IconButton>
      {open ? (
        <div className="ds-widget-menu__panel" role="menu" id={menuId}>
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              className="ds-widget-menu__item"
              disabled={item.disabled}
              onClick={() => {
                item.onSelect();
                setOpen(false);
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
