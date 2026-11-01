'use client';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { Conversation, MessageCategory } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';
import { investorChrome } from '../investor-labels';
import { useMessagingState } from '../../_state/messaging-state';

interface ConversationListProps {
  conversations: Conversation[];
  selectedId: string | null;
  onSelect?: (id: string) => void;
  showCheckbox?: boolean;
}

const PRIORITY_CLASS: Record<Conversation['priority'], string> = {
  urgent: 'inv-conv-list__priority--urgent',
  high: 'inv-conv-list__priority--high',
  normal: '',
  low: 'inv-conv-list__priority--low',
};

function formatRelativeTime(
  dateStr: string,
  justNow: string,
  hoursAgo: (count: number) => string,
  daysAgo: (count: number) => string,
): string {
  const date = new Date(dateStr);
  const now = new Date('2025-07-16T12:00:00Z');
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return justNow;
  if (diffHours < 24) return hoursAgo(diffHours);
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return daysAgo(diffDays);
  return formatInvestorDateTime(dateStr);
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  showCheckbox = false,
}: ConversationListProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tMessages = useTranslations('investorPortal.messages');
  const { selectedConversationIds, toggleConversationSelection } = useMessagingState();

  if (conversations.length === 0) {
    return (
      <div className="inv-conv-list__empty">
        <p>{tChrome('k571da4f5e8')}</p>
      </div>
    );
  }

  return (
    <ul className="inv-conv-list" role="listbox" aria-label={tChrome('k07c59b4412')}>
      {conversations.map((conv) => {
        const isSelected = selectedId === conv.id;
        const isChecked = selectedConversationIds.includes(conv.id);

        return (
          <li key={conv.id} role="presentation">
            <Link
              href={`/investor/messages/${conv.id}` as Route}
              className={`inv-conv-list__item${isSelected ? ' inv-conv-list__item--selected' : ''}${conv.unreadCount > 0 ? ' inv-conv-list__item--unread' : ''}`}
              role="option"
              aria-selected={isSelected}
              onClick={() => onSelect?.(conv.id)}
            >
              {showCheckbox ? (
                <input
                  type="checkbox"
                  className="inv-conv-list__checkbox"
                  checked={isChecked}
                  onChange={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    toggleConversationSelection(conv.id);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  aria-label={`${investorChrome(tChrome, 'Select')} ${investorChrome(tChrome, conv.subject)}`}
                />
              ) : null}

              <span className="inv-conv-list__avatar" aria-hidden="true">
                {conv.irMember.avatarInitials}
              </span>

              <div className="inv-conv-list__content">
                <div className="inv-conv-list__top">
                  <strong className="inv-conv-list__subject">{investorChrome(tChrome, conv.subject)}</strong>
                  <time className="inv-conv-list__time" dateTime={conv.lastMessageAt}>
                    {formatRelativeTime(
                      conv.lastMessageAt,
                      tMessages('justNow'),
                      (count) => tMessages('hoursAgo', { count }),
                      (count) => tMessages('daysAgo', { count }),
                    )}
                  </time>
                </div>
                <div className="inv-conv-list__middle">
                  <span className="inv-conv-list__project">{conv.investmentName}</span>
                  {conv.isStarred ? <span aria-label={tChrome('ke61561a80e')}>★</span> : null}
                  {conv.hasAttachments ? <span aria-label={tChrome('kfa7f9ec22a')}>📎</span> : null}
                </div>
                <p className="inv-conv-list__preview">{investorChrome(tChrome, conv.lastMessagePreview)}</p>
                <div className="inv-conv-list__badges">
                  <span className={`inv-conv-list__priority ${PRIORITY_CLASS[conv.priority]}`}>
                    {investorChrome(tChrome, conv.priority)}
                  </span>
                  <span className="inv-conv-list__category">
                    {investorChrome(tChrome, conv.messageType.replace(/_/g, ' '))}
                  </span>
                  {conv.unreadCount > 0 ? (
                    <span className="inv-conv-list__unread-badge" aria-label={tMessages('unread', { count: conv.unreadCount })}>
                      {conv.unreadCount}
                    </span>
                  ) : null}
                </div>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export type { MessageCategory };
