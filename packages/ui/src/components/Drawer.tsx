import type { ReactNode } from 'react';

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
  ariaLabel?: string;
}

export function Drawer({ open, onClose, title, children, footer, wide, ariaLabel }: DrawerProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="ih-drawer" role="presentation" onClick={onClose}>
      <aside
        className={`ih-drawer__panel${wide ? ' ih-drawer__panel--wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel ?? title}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="ih-drawer__header">
          <h2 className="ih-drawer__title">{title}</h2>
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
