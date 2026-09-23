'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { useInfiniteQuery } from '@tanstack/react-query';

import { EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import { fetchCommunicationThreads } from '@/workspaces/crm/api/communication';
import { communicationQueryKeys } from '@/workspaces/crm/hooks/use-communication';
import { useCommunicationUiStore } from '@/workspaces/crm/stores/communication-ui-store';
import type { CrmCommThreadSummary } from '@/workspaces/crm/types';

type CommunicationThreadListProps = {
  onSelectThread: (threadId: string) => void;
};

function formatRelativeDate(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  if (diffDays < 7) return date.toLocaleDateString([], { weekday: 'short' });
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

export function CommunicationThreadList({ onSelectThread }: CommunicationThreadListProps) {
  const t = useTranslations('crm.communication');
  const tChannels = useTranslations('crm.communication.channels');
  const selectedFolder = useCommunicationUiStore((s) => s.selectedFolder);
  const searchQuery = useCommunicationUiStore((s) => s.searchQuery);
  const selectedThreadId = useCommunicationUiStore((s) => s.selectedThreadId);
  const listRef = useRef<HTMLDivElement>(null);

  const folderParam = selectedFolder === 'all' ? undefined : selectedFolder;

  const query = useInfiniteQuery({
    queryKey: communicationQueryKeys.threads({ folder: folderParam, search: searchQuery || undefined }),
    queryFn: ({ pageParam = 1 }) =>
      fetchCommunicationThreads({
        folder: folderParam,
        search: searchQuery || undefined,
        page: pageParam,
        page_size: 30,
        sort_by: 'last_communication_at',
        sort_dir: 'desc',
      }),
    getNextPageParam: (lastPage) => (lastPage.page < lastPage.pages ? lastPage.page + 1 : undefined),
    initialPageParam: 1,
  });

  const threads: CrmCommThreadSummary[] = query.data?.pages.flatMap((p) => p.items) ?? [];

  const handleScroll = useCallback(() => {
    const el = listRef.current;
    if (!el || !query.hasNextPage || query.isFetchingNextPage) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) {
      void query.fetchNextPage();
    }
  }, [query]);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.addEventListener('scroll', handleScroll);
    return () => el.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  if (query.isLoading) {
    return <LoadingState label={t('loadingThreads')} />;
  }

  if (query.isError) {
    return <EmptyState title={t('loadFailed')} description={t('loadFailedHint')} />;
  }

  if (threads.length === 0) {
    return (
      <EmptyState
        title={t('emptyThreadsTitle')}
        description={t('emptyThreadsDescription')}
      />
    );
  }

  return (
    <div className="crm-communication__thread-list" ref={listRef}>
      {threads.map((thread) => {
        const isActive = thread.id === selectedThreadId;
        return (
          <button
            key={thread.id}
            type="button"
            className={
              isActive
                ? 'crm-communication__thread-item crm-communication__thread-item--active'
                : 'crm-communication__thread-item'
            }
            onClick={() => onSelectThread(thread.id)}
          >
            <div className="crm-communication__thread-item-top">
              <span className="crm-communication__thread-subject">
                {thread.is_pinned && <span aria-hidden="true">📌 </span>}
                {thread.subject || t('noSubject')}
              </span>
              <span className="crm-communication__thread-date">
                {formatRelativeDate(thread.last_communication_at)}
              </span>
            </div>
            <div className="crm-communication__thread-item-meta">
              <StatusChip tone="default">
                {tChannels(thread.channel)}
              </StatusChip>
              {thread.unread_count > 0 && (
                <span className="crm-communication__unread-badge">{thread.unread_count}</span>
              )}
            </div>
            {thread.preview && (
              <p className="crm-communication__thread-preview">{thread.preview}</p>
            )}
          </button>
        );
      })}
      {query.isFetchingNextPage && (
        <div className="crm-communication__thread-loading-more">
          <LoadingState label={t('loadingMore')} />
        </div>
      )}
    </div>
  );
}
