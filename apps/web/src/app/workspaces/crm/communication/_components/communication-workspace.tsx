'use client';

import { useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, LoadingState, SearchInput } from '@investhome/ui';

import { canCreateCommunications } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';
import { useCommunicationUiStore } from '@/workspaces/crm/stores/communication-ui-store';

import { CommunicationChannelHub } from './communication-channel-hub';
import { CommunicationComposer } from './communication-composer';
import { CommunicationConversationPanel } from './communication-conversation-panel';
import { CommunicationSidebar } from './communication-sidebar';
import { CommunicationThreadList } from './communication-thread-list';
import { ProviderStatusBadge } from './provider-status-badge';

export function CommunicationWorkspace() {
  const t = useTranslations('crm.communication');
  const tCommon = useTranslations('common');
  const { authLoading, user, canViewCommunications } = useCrmAccess();
  const panelCollapsed = useCommunicationUiStore((s) => s.panelCollapsed);
  const searchQuery = useCommunicationUiStore((s) => s.searchQuery);
  const setSearchQuery = useCommunicationUiStore((s) => s.setSearchQuery);
  const composerOpen = useCommunicationUiStore((s) => s.composerOpen);
  const setComposerOpen = useCommunicationUiStore((s) => s.setComposerOpen);
  const setSelectedThreadId = useCommunicationUiStore((s) => s.setSelectedThreadId);
  const setPanelCollapsed = useCommunicationUiStore((s) => s.setPanelCollapsed);

  const providersQuery = useQuery({
    ...communicationQueries.providers(),
    enabled: !authLoading && canViewCommunications,
  });

  const handleSelectThread = useCallback(
    (threadId: string) => {
      setSelectedThreadId(threadId);
      if (panelCollapsed === 'conversation') {
        setPanelCollapsed('none');
      }
    },
    [panelCollapsed, setPanelCollapsed, setSelectedThreadId],
  );

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canViewCommunications) {
    return (
      <ErrorState
        title={t('accessDenied')}
        message={t('accessDeniedHint')}
      />
    );
  }

  return (
    <div className="crm-communication">
      <header className="crm-communication__toolbar">
        <div className="crm-communication__toolbar-left">
          <Button
            type="button"
            variant="secondary"
            className="crm-communication__collapse-btn"
            onClick={() => setPanelCollapsed(panelCollapsed === 'folders' ? 'none' : 'folders')}
            aria-label={t('toggleFolders')}
          >
            ☰
          </Button>
          <SearchInput
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('searchPlaceholder')}
            aria-label={t('searchPlaceholder')}
          />
        </div>
        <div className="crm-communication__toolbar-right">
          {providersQuery.data?.items.slice(0, 2).map((p) => (
            <ProviderStatusBadge key={p.provider} status={p.status} />
          ))}
          {canCreateCommunications(user) && (
            <Button type="button" onClick={() => setComposerOpen(true)}>
              {t('compose')}
            </Button>
          )}
        </div>
      </header>

      <CommunicationChannelHub />

      <div className="crm-communication__layout">
        <CommunicationSidebar collapsed={panelCollapsed === 'folders'} />
        <section className="crm-communication__center" aria-label={t('threadListAriaLabel')}>
          <CommunicationThreadList onSelectThread={handleSelectThread} />
        </section>
        <CommunicationConversationPanel onCompose={() => setComposerOpen(true)} />
      </div>

      <CommunicationComposer open={composerOpen} onClose={() => setComposerOpen(false)} />
    </div>
  );
}
