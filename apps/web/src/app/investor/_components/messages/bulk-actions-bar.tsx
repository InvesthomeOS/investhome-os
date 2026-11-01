'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

import { useMessagingState } from '../../_state/messaging-state';

interface BulkActionsBarProps {
  visible: boolean;
}

export function BulkActionsBar({ visible }: BulkActionsBarProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const {
    selectedConversationIds,
    markConversationsRead,
    archiveConversations,
    clearConversationSelection,
  } = useMessagingState();

  if (!visible || selectedConversationIds.length === 0) return null;

  return (
    <div className="inv-bulk-actions" role="toolbar" aria-label={tChrome('k3268f92bfe')}>
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
      >{investorChrome(tChrome, "Archive")}</button>
      <button type="button" disabled title={tChrome('kbb23f6a3e1')}>
        Assign category
      </button>
      <button type="button" disabled title={tChrome('kbb23f6a3e1')}>
        Export
      </button>
      <button type="button" onClick={clearConversationSelection}>
        Clear
      </button>
    </div>
  );
}
