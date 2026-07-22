'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button, EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import {
  canCreateCommunications,
  canSendCommunications,
} from '@/lib/crm/crm-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { archiveThread, markThreadRead, pinThread } from '@/workspaces/crm/api/communication';
import { communicationQueries, communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';
import { useCommunicationUiStore } from '@/workspaces/crm/stores/communication-ui-store';

type CommunicationConversationPanelProps = {
  onCompose: () => void;
};

export function CommunicationConversationPanel({ onCompose }: CommunicationConversationPanelProps) {
  const t = useTranslations('crm.communication');
  const tChannels = useTranslations('crm.communication.channels');
  const tStatus = useTranslations('crm.communication.statuses');
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const selectedThreadId = useCommunicationUiStore((s) => s.selectedThreadId);
  const setComposerOpen = useCommunicationUiStore((s) => s.setComposerOpen);

  const threadQuery = useQuery(communicationQueries.threadDetail(selectedThreadId));

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: communicationQueryKeys.all });
  };

  const readMutation = useMutation({
    mutationFn: () => markThreadRead(selectedThreadId!),
    onSuccess: invalidate,
  });

  const pinMutation = useMutation({
    mutationFn: (pinned: boolean) => pinThread(selectedThreadId!, pinned),
    onSuccess: invalidate,
  });

  const archiveMutation = useMutation({
    mutationFn: () => archiveThread(selectedThreadId!),
    onSuccess: () => {
      useCommunicationUiStore.getState().setSelectedThreadId(null);
      invalidate();
    },
  });

  if (!selectedThreadId) {
    return (
      <div className="crm-communication__conversation crm-communication__conversation--empty">
        <EmptyState
          title={t('selectThreadTitle')}
          description={t('selectThreadDescription')}
          action={
            canCreateCommunications(user) ? (
              <Button type="button" onClick={onCompose}>
                {t('compose')}
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  if (threadQuery.isLoading) {
    return (
      <div className="crm-communication__conversation">
        <LoadingState label={t('loadingThread')} />
      </div>
    );
  }

  if (threadQuery.isError || !threadQuery.data) {
    return (
      <div className="crm-communication__conversation">
        <EmptyState title={t('threadLoadFailed')} />
      </div>
    );
  }

  const thread = threadQuery.data;

  return (
    <div className="crm-communication__conversation">
      <header className="crm-communication__conversation-header">
        <div>
          <h2 className="crm-communication__conversation-title">{thread.subject}</h2>
          <div className="crm-communication__conversation-meta">
            <StatusChip tone="default">
              {tChannels(thread.channel)}
            </StatusChip>
            <StatusChip tone="default">
              {tStatus(thread.status)}
            </StatusChip>
            {thread.message_count > 0 && (
              <span className="crm-communication__meta-text">
                {t('messageCount', { count: thread.message_count })}
              </span>
            )}
          </div>
        </div>
        <div className="crm-communication__conversation-actions">
          {canCreateCommunications(user) && (
            <Button type="button" onClick={() => setComposerOpen(true)}>
              {t('reply')}
            </Button>
          )}
          <Button
            type="button"
            variant="secondary"
            onClick={() => readMutation.mutate()}
          >
            {t('markRead')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => pinMutation.mutate(!thread.is_pinned)}
          >
            {thread.is_pinned ? t('unpin') : t('pin')}
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => archiveMutation.mutate()}
          >
            {t('archive')}
          </Button>
        </div>
      </header>

      <div className="crm-communication__messages">
        {thread.communications.length === 0 ? (
          <EmptyState title={t('noMessagesTitle')} description={t('noMessagesDescription')} />
        ) : (
          thread.communications.map((msg) => (
            <article key={msg.id} className="crm-communication__message">
              <div className="crm-communication__message-header">
                <StatusChip tone="default">
                  {tChannels(msg.channel)}
                </StatusChip>
                <StatusChip tone="default">
                  {tStatus(msg.status)}
                </StatusChip>
                <time className="crm-communication__message-time">
                  {new Date(msg.created_at).toLocaleString()}
                </time>
              </div>
              {msg.subject && <h3 className="crm-communication__message-subject">{msg.subject}</h3>}
              <p className="crm-communication__message-body">{msg.preview ?? '—'}</p>
              {msg.has_attachments && (
                <span className="crm-communication__attachment-indicator">{t('hasAttachments')}</span>
              )}
            </article>
          ))
        )}
      </div>

      {canSendCommunications(user) && (
        <footer className="crm-communication__conversation-footer">
          <p className="crm-communication__provider-note">{t('providerNote')}</p>
        </footer>
      )}
    </div>
  );
}
