'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { Announcement } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';
import { useMessagingState } from '../../_state/messaging-state';

interface AnnouncementsPanelProps {
  open: boolean;
  onClose: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function AnnouncementsPanel({ open, onClose }: AnnouncementsPanelProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tCommon = useTranslations('common');
  const { announcements, markAnnouncementRead, markAllAnnouncementsRead } = useMessagingState();

  if (!open) return null;

  return (
    <>
      <button
        type="button"
        className="inv-panel-overlay"
        onClick={onClose}
        aria-label={tChrome('k40bb648cd3')}
      />
      <aside
        className="inv-panel inv-panel--announcements"
        role="dialog"
        aria-labelledby="announcements-title"
        aria-modal="true"
      >
        <header className="inv-panel__header">
          <h2 id="announcements-title">{tChrome('kec105b2078')}</h2>
          <div className="inv-panel__header-actions">
            <button type="button" onClick={markAllAnnouncementsRead}>
              Mark all read
            </button>
            <button type="button" onClick={onClose} aria-label={tCommon('close')}>
              ×
            </button>
          </div>
        </header>

        <div className="inv-panel__body">
          {announcements.length === 0 ? (
            <p className="inv-panel__empty">{tChrome('kc32aa8cd5b')}</p>
          ) : (
            <ul className="inv-announcements-list">
              {announcements.map((ann: Announcement) => (
                <li
                  key={ann.id}
                  className={`inv-announcements-list__item${!ann.isRead ? ' inv-announcements-list__item--unread' : ''}`}
                >
                  <div className="inv-announcements-list__meta">
                    <span className="inv-announcements-list__category">{ann.category}</span>
                    <time dateTime={ann.publishedAt}>
                      {formatInvestorDateTime(ann.publishedAt)}
                    </time>
                  </div>
                  <h3>{ann.title}</h3>
                  <p>{ann.summary}</p>
                  {ann.attachments.length > 0 ? (
                    <ul className="inv-announcements-list__attachments">
                      {ann.attachments.map((att) => (
                        <li key={att.id}>
                          📎 {att.fileName} ({formatFileSize(att.fileSizeBytes)})
                        </li>
                      ))}
                    </ul>
                  ) : null}
                  <div className="inv-announcements-list__actions">
                    {!ann.isRead ? (
                      <button type="button" onClick={() => markAnnouncementRead(ann.id)}>
                        Mark read
                      </button>
                    ) : null}
                    {ann.actionHref ? (
                      <Link href={ann.actionHref as Route}>{ann.actionLabel ?? 'View'}</Link>
                    ) : ann.actionLabel ? (
                      <button type="button" disabled title={tChrome('kbb23f6a3e1')}>
                        {ann.actionLabel}
                      </button>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </>
  );
}
