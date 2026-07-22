'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect } from 'react';

import { getVisibleMessages } from '../../_data/conversations';
import type { Conversation } from '../../_data/messaging-types';
import { useMessagingState } from '../../_state/messaging-state';
import { ConversationTimeline } from './conversation-timeline';
import { MessageBubble } from './message-bubble';
import { MessageComposer } from './message-composer';

interface ConversationDetailProps {
  conversation: Conversation;
}

function formatDateSeparator(dateStr: string): string {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateStr));
}

function groupMessagesByDate(messages: Conversation['messages']) {
  const groups: { date: string; messages: Conversation['messages'] }[] = [];
  for (const msg of messages) {
    const date = msg.sentAt.split('T')[0] ?? msg.sentAt;
    const last = groups[groups.length - 1];
    if (last && last.date === date) {
      last.messages.push(msg);
    } else {
      groups.push({ date, messages: [msg] });
    }
  }
  return groups;
}

export function ConversationDetail({ conversation }: ConversationDetailProps) {
  const { markConversationRead, toggleStarConversation } = useMessagingState();
  const visibleMessages = getVisibleMessages(conversation);
  const groups = groupMessagesByDate(visibleMessages);
  const isStarred = conversation.isStarred;

  useEffect(() => {
    if (conversation.unreadCount > 0) {
      markConversationRead(conversation.id);
    }
  }, [conversation.id, conversation.unreadCount, markConversationRead]);

  return (
    <div className="inv-conv-detail">
      <header className="inv-conv-detail__header">
        <div>
          <h2 className="inv-conv-detail__subject">{conversation.subject}</h2>
          <p className="inv-conv-detail__meta">
            {conversation.investmentName} · {conversation.irMember.name} ·{' '}
            {conversation.irMember.role}
          </p>
        </div>
        <div className="inv-conv-detail__actions">
          <button
            type="button"
            className={`inv-conv-detail__star${isStarred ? ' inv-conv-detail__star--active' : ''}`}
            onClick={() => toggleStarConversation(conversation.id)}
            aria-pressed={isStarred}
            aria-label={isStarred ? 'Unstar conversation' : 'Star conversation'}
          >
            {isStarred ? '★' : '☆'}
          </button>
          <button type="button" className="inv-conv-detail__action" disabled title="Export (demo)">
            Export
          </button>
        </div>
      </header>

      {(conversation.relatedDocumentIds.length > 0 ||
        conversation.relatedSignatureIds.length > 0 ||
        conversation.relatedTaskIds.length > 0) && (
        <aside className="inv-conv-detail__refs" aria-label="Related items">
          {conversation.relatedTaskIds.map((id) => (
            <Link key={id} href={`/investor/tasks/${id}` as Route} className="inv-conv-detail__ref">
              Task: {id}
            </Link>
          ))}
          {conversation.relatedDocumentIds.map((id) => (
            <Link key={id} href={'/investor/documents' as Route} className="inv-conv-detail__ref">
              Document: {id}
            </Link>
          ))}
          {conversation.relatedSignatureIds.map((id) => (
            <Link key={id} href={'/investor/documents' as Route} className="inv-conv-detail__ref">
              Signature: {id}
            </Link>
          ))}
        </aside>
      )}

      <div className="inv-conv-detail__messages" role="log" aria-live="polite" aria-label="Messages">
        {groups.map((group) => (
          <div key={group.date}>
            <div className="inv-conv-detail__date-sep" role="separator">
              <span>{formatDateSeparator(group.date)}</span>
            </div>
            {group.messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </div>
        ))}
      </div>

      <ConversationTimeline events={conversation.timelineEvents} />

      <MessageComposer conversationId={conversation.id} />
    </div>
  );
}
