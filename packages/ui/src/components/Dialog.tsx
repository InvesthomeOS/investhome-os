import type { ReactNode } from 'react';

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  ariaLabel?: string;
}

export function Dialog({ open, onClose, title, children, footer, ariaLabel }: DialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="ih-dialog" role="presentation" onClick={onClose}>
      <div
        className="ih-dialog__panel"
        role="dialog"
        aria-modal="true"
        aria-label={ariaLabel ?? title}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="ih-dialog__header">
          <h2 className="ih-dialog__title">{title}</h2>
          <button type="button" className="ih-dialog__close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>
        <div className="ih-dialog__body">{children}</div>
        {footer ? <footer className="ih-dialog__footer">{footer}</footer> : null}
      </div>
    </div>
  );
}
