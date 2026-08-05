'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';

export type FocusSecondaryTrayProps = {
  label: string;
  count: number;
  /** When set, renders label + this subtitle instead of `Label (count)`. */
  countLabel?: string;
  open: boolean;
  pinned: boolean;
  onToggle: () => void;
  onClose: () => void;
  children: ReactNode;
  testId?: string;
  handleTestId?: string;
};

/**
 * Collapsible secondary content tray (filmstrip / timeline / variations / structure).
 * Unpinned FS: collapsed handle by default; open overlays canvas (does not resize stage).
 * Pinned / normal: always expanded in document flow.
 */
export function FocusSecondaryTray({
  label,
  count,
  countLabel,
  open,
  pinned,
  onToggle,
  onClose,
  children,
  testId = 'cs-fw-tray',
  handleTestId = 'cs-fw-tray-handle',
}: FocusSecondaryTrayProps) {
  const t = useTranslations('creativeStudio.focusWorkspace');
  const compactTitle = countLabel ? `${label} · ${countLabel}` : `${label} (${count})`;
  const ariaTitle = compactTitle;

  const titleNode = countLabel ? (
    <div className="cs-fw-tray__heading">
      <h3 className="cs-fw-tray__title">{label}</h3>
      <span className="cs-fw-tray__count">{countLabel}</span>
    </div>
  ) : (
    <h3 className="cs-fw-tray__title">{compactTitle}</h3>
  );

  if (pinned) {
    return (
      <div className="cs-fw-tray cs-fw-tray--pinned" data-testid={testId} data-open="true">
        <div className="cs-fw-tray__chrome">
          {titleNode}
          <span className="cs-fw-tray__hint">{t('tray.hint')}</span>
        </div>
        <div className="cs-fw-tray__body">{children}</div>
      </div>
    );
  }

  return (
    <div
      className={['cs-fw-tray', 'cs-fw-tray--overlay', open ? 'is-open' : 'is-collapsed']
        .filter(Boolean)
        .join(' ')}
      data-testid={testId}
      data-open={open ? 'true' : 'false'}
    >
      <button
        type="button"
        className="cs-fw-tray__handle"
        data-testid={handleTestId}
        aria-expanded={open}
        aria-controls={`${testId}-panel`}
        onClick={onToggle}
      >
        <IhIcon name={open ? 'chevronDown' : 'chevronRight'} size={12} />
        <span>{compactTitle}</span>
      </button>
      {open ? (
        <div
          id={`${testId}-panel`}
          className="cs-fw-tray__panel"
          role="region"
          aria-label={ariaTitle}
        >
          <div className="cs-fw-tray__chrome">
            {titleNode}
            <button
              type="button"
              className="cs-fw-tray__close"
              data-testid={`${testId}-close`}
              aria-label={t('tray.close')}
              onClick={onClose}
            >
              <span aria-hidden="true">×</span>
            </button>
          </div>
          <div className="cs-fw-tray__body">{children}</div>
        </div>
      ) : null}
    </div>
  );
}
