'use client';

import type { TimelineEvent } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';

interface ConversationTimelineProps {
  events: TimelineEvent[];
}

const TYPE_ICONS: Record<TimelineEvent['type'], string> = {
  construction: '🏗',
  distribution: '$',
  document: '📄',
  task: '☑',
  signature: '✍',
  project_update: '↗',
  message: '✉',
};

export function ConversationTimeline({ events }: ConversationTimelineProps) {
  if (events.length === 0) return null;

  return (
    <section className="inv-conv-timeline" aria-label="Project timeline">
      <h3 className="inv-conv-timeline__title">Project Timeline</h3>
      <ol className="inv-conv-timeline__list">
        {events.map((event) => (
          <li key={event.id} className="inv-conv-timeline__item">
            <span className="inv-conv-timeline__icon" aria-hidden="true">
              {TYPE_ICONS[event.type]}
            </span>
            <div className="inv-conv-timeline__content">
              <strong>{event.title}</strong>
              <p>{event.description}</p>
              <time dateTime={event.timestamp}>{formatInvestorDateTime(event.timestamp)}</time>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
