'use client';

import { useMemo, useState } from 'react';

import {
  DEFAULT_CONVERSATION_FILTERS,
  DEFAULT_CONVERSATION_SORT,
  filterConversations,
  getCategoryCounts,
  globalMessagingSearch,
  sortConversations,
} from '../../_data/messaging-calculations';
import type { ConversationFilterState, ConversationSortState, MessageCategory } from '../../_data/messaging-types';
import { EmptyState } from '../empty-state';
import { useMessagingState } from '../../_state/messaging-state';
import { AnnouncementsPanel } from './announcements-panel';
import { BulkActionsBar } from './bulk-actions-bar';
import { CategorySidebar } from './category-sidebar';
import { ComposeModal } from './compose-modal';
import { ConversationList } from './conversation-list';
import { GlobalSearchPanel } from './global-search-panel';
import { MessagesFilters } from './messages-filters';
import { MessagesHeader } from './messages-header';
import { MessagesKpiRow } from './messages-kpi-row';
import { MessagesLayout } from './messages-layout';
import { MessagesSearchBar } from './messages-search-bar';
import { NotificationsPanel } from './notifications-panel';

interface MessagesViewProps {
  selectedConversationId?: string | null;
  mainContent?: React.ReactNode;
}

export function MessagesView({ selectedConversationId = null, mainContent }: MessagesViewProps) {
  const { conversations, announcements, notifications, tasks, messagesSummary } =
    useMessagingState();

  const [category, setCategory] = useState<MessageCategory>('inbox');
  const [filters, setFilters] = useState<ConversationFilterState>(DEFAULT_CONVERSATION_FILTERS);
  const [sort, setSort] = useState<ConversationSortState>(DEFAULT_CONVERSATION_SORT);
  const [globalQuery, setGlobalQuery] = useState('');
  const [composeOpen, setComposeOpen] = useState(false);
  const [announcementsOpen, setAnnouncementsOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [bulkMode, setBulkMode] = useState(false);

  const activeFilters = useMemo(
    () => ({ ...filters, category, search: filters.search }),
    [filters, category],
  );

  const filtered = useMemo(
    () => sortConversations(filterConversations(conversations, activeFilters), sort),
    [conversations, activeFilters, sort],
  );

  const categoryCounts = useMemo(() => getCategoryCounts(conversations), [conversations]);

  const searchResults = useMemo(
    () => globalMessagingSearch(conversations, announcements, notifications, tasks, globalQuery),
    [conversations, announcements, notifications, tasks, globalQuery],
  );

  const handleFiltersChange = (patch: Partial<ConversationFilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  };

  const handleCategoryChange = (cat: MessageCategory) => {
    setCategory(cat);
    setFilters((prev) => ({
      ...prev,
      category: cat,
      archivedOnly: cat === 'archived',
    }));
  };

  return (
    <div className="investor-page inv-messages-page">
      <MessagesHeader
        onCompose={() => setComposeOpen(true)}
        onAnnouncements={() => setAnnouncementsOpen(true)}
        onNotifications={() => setNotificationsOpen(true)}
        unreadAnnouncements={messagesSummary.unreadAnnouncements}
        unreadNotifications={messagesSummary.unreadNotifications}
      />

      <MessagesKpiRow summary={messagesSummary} />

      <div className="inv-messages-page__toolbar">
        <MessagesSearchBar
          value={globalQuery || filters.search}
          onChange={(v) => {
            setGlobalQuery(v);
            handleFiltersChange({ search: v });
          }}
        />
        <button
          type="button"
          className={`inv-messages-page__bulk-toggle${bulkMode ? ' inv-messages-page__bulk-toggle--active' : ''}`}
          onClick={() => setBulkMode((b) => !b)}
          aria-pressed={bulkMode}
        >
          Bulk actions
        </button>
      </div>

      <GlobalSearchPanel
        results={searchResults}
        query={globalQuery}
        onClose={() => setGlobalQuery('')}
      />

      <BulkActionsBar visible={bulkMode} />

      <MessagesLayout
        sidebar={
          <CategorySidebar
            activeCategory={category}
            onCategoryChange={handleCategoryChange}
            counts={categoryCounts}
          />
        }
        list={
          <>
            <MessagesFilters
              filters={activeFilters}
              sort={sort}
              onFiltersChange={handleFiltersChange}
              onSortChange={setSort}
            />
            <ConversationList
              conversations={filtered}
              selectedId={selectedConversationId}
              showCheckbox={bulkMode}
            />
          </>
        }
        main={
          mainContent ?? (
            <EmptyState
              icon="✉"
              title="Select a conversation"
              description="Choose a conversation from the list to view messages, or compose a new message to your relationship manager."
              actionLabel="Compose message"
              onAction={() => setComposeOpen(true)}
            />
          )
        }
      />

      <ComposeModal open={composeOpen} onClose={() => setComposeOpen(false)} />
      <AnnouncementsPanel open={announcementsOpen} onClose={() => setAnnouncementsOpen(false)} />
      <NotificationsPanel open={notificationsOpen} onClose={() => setNotificationsOpen(false)} />
    </div>
  );
}
