'use client';

import { useTranslations } from 'next-intl';

import { investorChrome } from '@/app/investor/_components/investor-labels';
import type { TimelineEvent, TimelineEventType } from '../_data/types';
import { formatInvestorDateTime } from '../_data/mock-data';

const EVENT_ICONS: Record<TimelineEventType, string> = {
  distribution: '$',
  document: '📄',
  message: '✉',
  investment: '◆',
  signature: '✎',
  task: '☑',
};

export interface ActivityTimelineProps {
  events: TimelineEvent[];
  locale?: string;
  maxItems?: number;
}

export function ActivityTimeline({ events, locale = 'en-US', maxItems }: ActivityTimelineProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const visible = maxItems ? events.slice(0, maxItems) : events;

  if (visible.length === 0) {
    return <p className="inv-section-header__subtitle">{tChrome('k107fe2b93d')}</p>;
  }

  return (
    <ul className="inv-timeline" aria-label={tChrome('k72d5617f3f')}>
      {visible.map((event) => (
        <li key={event.id} className="inv-timeline__item">
          <span
            className={`inv-timeline__icon inv-timeline__icon--${event.type}`}
            aria-hidden="true"
          >
            {EVENT_ICONS[event.type]}
          </span>
          <div className="inv-timeline__body">
            <p className="inv-timeline__title">{investorChrome(tChrome, event.title)}</p>
            <p className="inv-timeline__description">{investorChrome(tChrome, event.description)}</p>
            <time className="inv-timeline__time" dateTime={event.timestamp}>
              {formatInvestorDateTime(event.timestamp, locale)}
            </time>
          </div>
        </li>
      ))}
    </ul>
  );
}
