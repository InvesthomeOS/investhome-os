'use client';

import { useLocale, useTranslations } from 'next-intl';

import { StatusChip } from '@investhome/ui';

import { emailPreviewText } from '@/workspaces/crm/contact-card/history-html';
import type { CrmActivitySummary, CrmTimelineEntry } from '@/workspaces/crm/types/activities';

const TYPE_ICONS: Record<string, string> = {
  note: '📝',
  phone_call: '📞',
  email: '✉️',
  whatsapp: '💬',
  meeting: '📅',
  task: '✅',
  follow_up: '🔔',
  system_event: '⚙️',
  default: '📌',
};

type ActivityCardProps = {
  item: CrmActivitySummary | CrmTimelineEntry;
  compact?: boolean;
  onSelect?: (id: string) => void;
  selected?: boolean;
};

export function ActivityCard({ item, compact = false, onSelect, selected = false }: ActivityCardProps) {
  const t = useTranslations('crm.activities');
  const locale = useLocale();
  const isTimeline = 'source' in item;
  const activityType = isTimeline ? item.activity_type : item.activity_type;
  const createdAt = item.created_at;
  const id = item.id.replace(/^log-/, '');
  const title = item.title;
  const summary = isTimeline ? item.summary : 'summary' in item ? item.summary : null;
  const status = isTimeline ? item.status : 'status' in item ? item.status : null;
  const priority = isTimeline ? item.priority : 'priority' in item ? item.priority : null;

  const formatter = new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: compact ? undefined : 'short',
  });

  const icon = TYPE_ICONS[activityType] ?? TYPE_ICONS.default;

  return (
    <article
      className={
        selected
          ? 'crm-activity-card crm-activity-card--selected'
          : 'crm-activity-card'
      }
      role="button"
      tabIndex={0}
      onClick={() => onSelect?.(id)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onSelect?.(id);
        }
      }}
    >
      <div className="crm-activity-card__header">
        <span className="crm-activity-card__icon" aria-hidden="true">
          {icon}
        </span>
        <div className="crm-activity-card__meta">
          <span className="crm-activity-card__type">{t(`types.${activityType}` as 'types.note')}</span>
          <time className="crm-activity-card__time" dateTime={createdAt}>
            {formatter.format(new Date(createdAt))}
          </time>
        </div>
        {status && (
          <StatusChip tone="default">{t(`statuses.${status}` as 'statuses.planned')}</StatusChip>
        )}
      </div>
      <h3 className="crm-activity-card__title">{title}</h3>
      {!compact && summary && (
        <p className="crm-activity-card__summary">{emailPreviewText(summary)}</p>
      )}
      {!compact && priority && (
        <span className="crm-activity-card__priority">
          {t(`priorities.${priority}` as 'priorities.medium')}
        </span>
      )}
      {isTimeline && item.is_system_event && (
        <span className="crm-activity-card__badge">{t('systemEvent')}</span>
      )}
    </article>
  );
}
