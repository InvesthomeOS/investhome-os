'use client';

import { useMessagingState } from '../../_state/messaging-state';

interface BulkActionsBarProps {
  visible: boolean;
}

export function BulkActionsBar({ visible }: BulkActionsBarProps) {
  const {
    selectedConversationIds,
    markConversationsRead,
    archiveConversations,
    clearConversationSelection,
  } = useMessagingState();

  if (!visible || selectedConversationIds.length === 0) return null;

  return (
    <div className="inv-bulk-actions" role="toolbar" aria-label="Bulk actions">
      <span className="inv-bulk-actions__count">
        {selectedConversationIds.length} selected
      </span>
      <button
        type="button"
        onClick={() => markConversationsRead(selectedConversationIds)}
      >
        Mark read
      </button>
      <button
        type="button"
        onClick={() => archiveConversations(selectedConversationIds)}
      >
        Archive
      </button>
      <button type="button" disabled title="Demo only">
        Assign category
      </button>
      <button type="button" disabled title="Demo only">
        Export
      </button>
      <button type="button" onClick={clearConversationSelection}>
        Clear
      </button>
    </div>
  );
}
