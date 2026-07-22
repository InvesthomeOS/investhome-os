'use client';

import { useCallback, useState } from 'react';

import type { InvestmentDetail, InvestmentUpdate } from '../../_data/investment-detail-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

const CATEGORY_LABELS: Record<string, string> = {
  construction: 'Construction',
  financial: 'Financial',
  legal: 'Legal',
  market: 'Market',
  operations: 'Operations',
  investor_relations: 'Investor Relations',
};

export interface UpdatesTimelineProps {
  detail: InvestmentDetail;
  onPlaceholderAction: (message: string) => void;
}

export function UpdatesTimeline({ detail, onPlaceholderAction }: UpdatesTimelineProps) {
  const [updates, setUpdates] = useState<InvestmentUpdate[]>(detail.updates);
  const unreadCount = updates.filter((u) => !u.isRead).length;

  const markAsRead = useCallback((id: string) => {
    setUpdates((prev) =>
      prev.map((u) => (u.id === id ? { ...u, isRead: true } : u)),
    );
  }, []);

  return (
    <section className="inv-detail-panel" aria-labelledby="updates-heading">
      <SectionHeader
        title="Updates"
        subtitle={unreadCount > 0 ? `${unreadCount} unread update${unreadCount > 1 ? 's' : ''}` : 'All updates read'}
      />

      <ul className="inv-detail-updates" aria-label="Investment updates">
        {updates.map((update) => (
          <li
            key={update.id}
            className={`inv-detail-updates__item${update.isRead ? '' : ' inv-detail-updates__item--unread'}`}
          >
            <div className="inv-detail-updates__header">
              <span className={`inv-detail-updates__category inv-detail-updates__category--${update.category}`}>
                {CATEGORY_LABELS[update.category] ?? update.category}
              </span>
              {!update.isRead ? (
                <span className="inv-detail-updates__unread-badge" aria-label="Unread">
                  New
                </span>
              ) : null}
            </div>
            <h3 className="inv-detail-updates__title">{update.title}</h3>
            <p className="inv-detail-updates__summary">{update.summary}</p>
            <div className="inv-detail-updates__footer">
              <span className="inv-detail-updates__author">{update.author}</span>
              <time dateTime={update.date}>{formatInvestorDate(update.date)}</time>
            </div>
            <div className="inv-detail-updates__actions">
              {!update.isRead ? (
                <button
                  type="button"
                  className="inv-detail-updates__btn"
                  onClick={() => markAsRead(update.id)}
                >
                  Mark as Read
                </button>
              ) : null}
              <button
                type="button"
                className="inv-detail-updates__btn"
                onClick={() => onPlaceholderAction(`Full update view for "${update.title}" coming soon.`)}
              >
                View Full Update
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
