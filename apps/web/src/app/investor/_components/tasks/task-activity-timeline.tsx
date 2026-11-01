'use client';

import { useTranslations } from 'next-intl';

import type { TaskActivity } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';

interface TaskActivityTimelineProps {
  activity: TaskActivity[];
}

const TYPE_ICONS: Record<TaskActivity['type'], string> = {
  created: '+',
  updated: '↻',
  comment: '💬',
  status_change: '◆',
  attachment: '📎',
  reminder: '⏰',
};

export function TaskActivityTimeline({ activity }: TaskActivityTimelineProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  if (activity.length === 0) return null;

  return (
    <section className="inv-task-activity" aria-labelledby="activity-title">
      <h3 id="activity-title">{tChrome('k81c0d915fa')}</h3>
      <ol className="inv-task-activity__list">
        {activity.map((item) => (
          <li key={item.id} className="inv-task-activity__item">
            <span className="inv-task-activity__icon" aria-hidden="true">
              {TYPE_ICONS[item.type]}
            </span>
            <div>
              <p>{item.description}</p>
              <span className="inv-task-activity__meta">
                {item.actor} · <time dateTime={item.timestamp}>{formatInvestorDateTime(item.timestamp)}</time>
              </span>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
