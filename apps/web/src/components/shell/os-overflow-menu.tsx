'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useId, useRef, useState } from 'react';

export type OsOverflowItem = {
  id: string;
  label?: string;
  href?: Route;
  onSelect?: () => void;
  destructive?: boolean;
  testId?: string;
  hidden?: boolean;
  divider?: boolean;
};

export function OsOverflowMenu({
  label,
  items,
}: {
  label: string;
  items: OsOverflowItem[];
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuId = useId();
  const visible = items.filter((item) => !item.hidden);

  useEffect(() => {
    if (!open) return undefined;
    const close = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [open]);

  if (!visible.length) return null;

  return (
    <div className="os-overflow" ref={rootRef}>
      <button
        type="button"
        className="os-overflow__trigger"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        data-testid="os-overflow-trigger"
        onClick={() => setOpen((current) => !current)}
      >
        <span aria-hidden="true" data-testid="os-overflow-ellipsis">⋯</span>
      </button>
      {open ? (
        <div className="os-overflow__menu" id={menuId} role="menu">
          {visible.map((item) =>
            item.divider ? (
              <hr key={item.id} className="os-overflow__divider" />
            ) : item.href ? (
              <Link key={item.id} href={item.href} role="menuitem" className="os-overflow__item" data-testid={item.testId} onClick={() => setOpen(false)}>
                {item.label}
              </Link>
            ) : (
              <button
                key={item.id}
                type="button"
                role="menuitem"
                className={`os-overflow__item${item.destructive ? ' is-destructive' : ''}`}
                data-testid={item.testId}
                onClick={() => {
                  setOpen(false);
                  item.onSelect?.();
                }}
              >
                {item.label}
              </button>
            ),
          )}
        </div>
      ) : null}
    </div>
  );
}
