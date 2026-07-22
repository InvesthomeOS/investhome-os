'use client';

import { useLocale, useTranslations } from 'next-intl';

import { Button, EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import type { CrmActivityDetail } from '@/workspaces/crm/types/activities';

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
          {activity.summary && <p className="crm-activity-detail__summary">{activity.summary}</p>}
          {activity.description && (
            <section>
              <h4>{t('description')}</h4>
              <p>{activity.description}</p>
            </section>
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
