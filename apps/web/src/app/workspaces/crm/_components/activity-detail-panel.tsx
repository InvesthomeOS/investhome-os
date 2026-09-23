'use client';

import { useLocale, useTranslations } from 'next-intl';

import { Button, EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import { escapeHtml, parseEmailContent, stripHtml } from '@/workspaces/crm/contact-card/history-html';
import type { CrmActivityDetail } from '@/workspaces/crm/types/activities';

import '@/workspaces/crm/contact-card/contact-card.css';

type ActivityDetailPanelProps = {
  activity: CrmActivityDetail | undefined;
  loading: boolean;
  error?: string;
  onClose: () => void;
  onComplete?: (id: string) => void;
};

export function ActivityDetailPanel({
  activity,
  loading,
  error,
  onClose,
  onComplete,
}: ActivityDetailPanelProps) {
  const t = useTranslations('crm.activities.detail');
  const locale = useLocale();
  const formatter = new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <aside className="crm-activity-detail">
      <header className="crm-activity-detail__header">
        <h2>{t('title')}</h2>
        <button type="button" className="crm-modal__close" onClick={onClose} aria-label={t('close')}>
          ×
        </button>
      </header>

      {loading && <LoadingState label={t('loading')} />}
      {error && !loading && <EmptyState title={t('loadFailed')} description={error} />}
      {!loading && activity && (
        <div className="crm-activity-detail__body">
          <div className="crm-activity-detail__badges">
            <StatusChip tone="default">{activity.activity_type}</StatusChip>
            <StatusChip tone="default">{activity.status}</StatusChip>
            {activity.priority && <StatusChip tone="warning">{activity.priority}</StatusChip>}
          </div>
          <h3>{activity.title}</h3>
          {activity.activity_type === 'email' ? (
            <SanitizedActivityEmail activity={activity} />
          ) : (
            <>
              {activity.summary && (
                <p className="crm-activity-detail__summary">{stripHtml(activity.summary)}</p>
              )}
              {activity.description && (
                <section>
                  <h4>{t('description')}</h4>
                  <p>{stripHtml(activity.description)}</p>
                </section>
              )}
            </>
          )}
          <dl className="crm-activity-detail__meta">
            <div>
              <dt>{t('created')}</dt>
              <dd>{formatter.format(new Date(activity.created_at))}</dd>
            </div>
            {activity.due_date && (
              <div>
                <dt>{t('dueDate')}</dt>
                <dd>{formatter.format(new Date(activity.due_date))}</dd>
              </div>
            )}
            {activity.location && (
              <div>
                <dt>{t('location')}</dt>
                <dd>{activity.location}</dd>
              </div>
            )}
            {activity.meeting_url && (
              <div>
                <dt>{t('meetingUrl')}</dt>
                <dd>
                  <a href={activity.meeting_url} target="_blank" rel="noreferrer">
                    {activity.meeting_url}
                  </a>
                </dd>
              </div>
            )}
          </dl>

          {activity.checklist_items.length > 0 && (
            <section>
              <h4>{t('checklist')}</h4>
              <ul className="crm-activity-detail__checklist">
                {activity.checklist_items.map((item) => (
                  <li key={item.id} className={item.is_completed ? 'is-completed' : undefined}>
                    {item.title}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {activity.comments.length > 0 && (
            <section>
              <h4>{t('comments')}</h4>
              <ul className="crm-activity-detail__comments">
                {activity.comments.map((comment) => (
                  <li key={comment.id}>{comment.body}</li>
                ))}
              </ul>
            </section>
          )}

          {activity.activity_type === 'task' && activity.status !== 'completed' && onComplete && (
            <Button type="button" onClick={() => onComplete(activity.id)}>
              {t('completeTask')}
            </Button>
          )}
        </div>
      )}
    </aside>
  );
}

function SanitizedActivityEmail({ activity }: { activity: CrmActivityDetail }) {
  const parsed = parseEmailContent(activity.title, activity.description || activity.summary);
  const html = parsed.html || `<p>${escapeHtml(parsed.text).replace(/\n/g, '<br>')}</p>`;
  return (
    <div
      className="crm-email-detail__body"
      data-testid="email-sanitized-body"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
