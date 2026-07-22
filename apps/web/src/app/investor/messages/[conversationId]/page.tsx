'use client';

import { useParams } from 'next/navigation';
import { useMemo } from 'react';

import { ConversationDetail } from '../../_components/messages/conversation-detail';
import { MessagesView } from '../../_components/messages/messages-view';
import { EmptyState } from '../../_components/empty-state';
import { useMessagingState } from '../../_state/messaging-state';

export default function ConversationDetailPage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;
  const { conversations } = useMessagingState();

  const conversation = useMemo(
    () => conversations.find((c) => c.id === conversationId),
    [conversations, conversationId],
  );

  if (!conversation) {
    return (
      <MessagesView
        selectedConversationId={conversationId}
        mainContent={
          <EmptyState
            icon="✉"
            title="Conversation not found"
            description="This conversation may have been removed or archived."
          />
        }
      />
    );
  }

  return (
    <MessagesView
      selectedConversationId={conversationId}
      mainContent={<ConversationDetail conversation={conversation} />}
    />
  );
}
