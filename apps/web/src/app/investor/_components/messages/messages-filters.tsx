'use client';

import type { ConversationFilterState, ConversationSortState } from '../../_data/messaging-types';
import { getAllInvestments } from '../../_data/investments';

interface MessagesFiltersProps {
  filters: ConversationFilterState;
  sort: ConversationSortState;
  onFiltersChange: (patch: Partial<ConversationFilterState>) => void;
  onSortChange: (sort: ConversationSortState) => void;
}

export function MessagesFilters({
  filters,
  sort,
  onFiltersChange,
  onSortChange,
}: MessagesFiltersProps) {
  const investments = getAllInvestments();

  return (
    <div className="inv-msg-filters" role="search" aria-label="Filter conversations">
      <select
        className="inv-msg-filters__select"
        value={filters.investmentId}
        onChange={(e) => onFiltersChange({ investmentId: e.target.value })}
        aria-label="Filter by investment"
      >
        <option value="all">All investments</option>
        {investments.map((inv) => (
          <option key={inv.id} value={inv.id}>
            {inv.projectName}
          </option>
        ))}
      </select>

      <select
        className="inv-msg-filters__select"
        value={filters.priority}
        onChange={(e) =>
          onFiltersChange({
            priority: e.target.value as ConversationFilterState['priority'],
          })
        }
        aria-label="Filter by priority"
      >
        <option value="all">All priorities</option>
        <option value="urgent">Urgent</option>
        <option value="high">High</option>
        <option value="normal">Normal</option>
        <option value="low">Low</option>
      </select>

      <select
        className="inv-msg-filters__select"
        value={filters.status}
        onChange={(e) =>
          onFiltersChange({
            status: e.target.value as ConversationFilterState['status'],
          })
        }
        aria-label="Filter by status"
      >
        <option value="all">All statuses</option>
        <option value="active">Active</option>
        <option value="archived">Archived</option>
        <option value="closed">Closed</option>
      </select>

      <label className="inv-msg-filters__check">
        <input
          type="checkbox"
          checked={filters.unreadOnly}
          onChange={(e) => onFiltersChange({ unreadOnly: e.target.checked })}
        />
        Unread only
      </label>

      <label className="inv-msg-filters__check">
        <input
          type="checkbox"
          checked={filters.hasAttachments === true}
          onChange={(e) =>
            onFiltersChange({ hasAttachments: e.target.checked ? true : null })
          }
        />
        Has attachments
      </label>

      <select
        className="inv-msg-filters__select"
        value={`${sort.field}-${sort.direction}`}
        onChange={(e) => {
          const [field, direction] = e.target.value.split('-') as [
            ConversationSortState['field'],
            ConversationSortState['direction'],
          ];
          onSortChange({ field, direction });
        }}
        aria-label="Sort conversations"
      >
        <option value="lastMessageAt-desc">Newest first</option>
        <option value="lastMessageAt-asc">Oldest first</option>
        <option value="subject-asc">Subject A–Z</option>
        <option value="priority-asc">Priority</option>
        <option value="unreadCount-desc">Most unread</option>
      </select>
    </div>
  );
}
