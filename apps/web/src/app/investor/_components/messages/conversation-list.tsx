'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { Conversation, MessageCategory } from '../../_data/messaging-types';
import { formatInvestorDateTime } from '../../_data/mock-data';
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

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date('2025-07-16T12:00:00Z');
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatInvestorDateTime(dateStr);
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  showCheckbox = false,
}: ConversationListProps) {
  const { selectedConversationIds, toggleConversationSelection } = useMessagingState();

  if (conversations.length === 0) {
    return (
      <div className="inv-conv-list__empty">
        <p>No conversations match your filters.</p>
      </div>
    );
  }

  return (
    <ul className="inv-conv-list" role="listbox" aria-label="Conversations">
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
                  aria-label={`Select ${conv.subject}`}
                />
              ) : null}

              <span className="inv-conv-list__avatar" aria-hidden="true">
                {conv.irMember.avatarInitials}
              </span>

              <div className="inv-conv-list__content">
                <div className="inv-conv-list__top">
                  <strong className="inv-conv-list__subject">{conv.subject}</strong>
                  <time className="inv-conv-list__time" dateTime={conv.lastMessageAt}>
                    {formatRelativeTime(conv.lastMessageAt)}
                  </time>
                </div>
                <div className="inv-conv-list__middle">
                  <span className="inv-conv-list__project">{conv.investmentName}</span>
                  {conv.isStarred ? <span aria-label="Starred">★</span> : null}
                  {conv.hasAttachments ? <span aria-label="Has attachments">📎</span> : null}
                </div>
                <p className="inv-conv-list__preview">{conv.lastMessagePreview}</p>
                <div className="inv-conv-list__badges">
                  <span className={`inv-conv-list__priority ${PRIORITY_CLASS[conv.priority]}`}>
                    {conv.priority}
                  </span>
                  <span className="inv-conv-list__category">{conv.messageType.replace(/_/g, ' ')}</span>
                  {conv.unreadCount > 0 ? (
                    <span className="inv-conv-list__unread-badge" aria-label={`${conv.unreadCount} unread`}>
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
