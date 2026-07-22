'use client';

import { useEffect, useId, useRef, type MouseEvent, type ReactNode } from 'react';

export type DrawerSize = 'sm' | 'md' | 'lg' | 'full';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  /** @deprecated Prefer `size="lg"`. Kept for existing callers. */
  wide?: boolean;
  /** sm=320 · md=420 · lg=640 · full=100vw */
  size?: DrawerSize;
  subtitle?: string;
  ariaLabel?: string;
}

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute('disabled') && el.getAttribute('aria-hidden') !== 'true');
}

function resolveSizeClass(size: DrawerSize | undefined, wide: boolean | undefined): string {
  if (size === 'sm') return ' ih-drawer__panel--sm';
  if (size === 'lg' || (!size && wide)) return ' ih-drawer__panel--wide';
  if (size === 'full') return ' ih-drawer__panel--full';
  return '';
}

export function Drawer({
  open,
  onClose,
  title,
  children,
  footer,
  wide,
  size,
  subtitle,
  ariaLabel,
}: DrawerProps) {
  const panelRef = useRef<HTMLElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);
  const titleId = useId();
  const subtitleId = useId();

  useEffect(() => {
    if (!open) return;

    previouslyFocused.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const panel = panelRef.current;
    const focusables = panel ? getFocusable(panel) : [];
    (focusables[0] ?? panel)?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab' || !panel) return;
      const items = getFocusable(panel);
      if (items.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }
      const first = items[0]!;
      const last = items[items.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused.current?.focus?.();
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="ih-drawer" role="presentation" onClick={onClose}>
      <aside
        ref={panelRef}
        className={`ih-drawer__panel${resolveSizeClass(size, wide)}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={subtitle ? subtitleId : undefined}
        aria-label={ariaLabel ?? title}
        tabIndex={-1}
        onClick={(event: MouseEvent) => event.stopPropagation()}
      >
        <header className="ih-drawer__header">
          <div>
            <h2 id={titleId} className="ih-drawer__title">
              {title}
            </h2>
            {subtitle ? (
              <p id={subtitleId} className="ih-drawer__subtitle">
                {subtitle}
              </p>
            ) : null}
          </div>
          <button type="button" className="ih-drawer__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <div className="ih-drawer__body">{children}</div>
        {footer ? <footer className="ih-drawer__footer">{footer}</footer> : null}
      </aside>
    </div>
  );
}
