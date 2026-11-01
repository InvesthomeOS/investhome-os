'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

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
  const tChrome = useTranslations('investorPortal.chrome');
  const investments = getAllInvestments();

  return (
    <div className="inv-msg-filters" role="search" aria-label={tChrome('ka70369ae33')}>
      <select
        className="inv-msg-filters__select"
        value={filters.investmentId}
        onChange={(e) => onFiltersChange({ investmentId: e.target.value })}
        aria-label={tChrome('k3132ed40f5')}
      >
        <option value="all">{tChrome('k294eded6ec')}</option>
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
        aria-label={tChrome('k870c2d046e')}
      >
        <option value="all">{tChrome('kbc6ba0d1bb')}</option>
        <option value="urgent">{tChrome('kecb26f46e3')}</option>
        <option value="high">{tChrome('kb1a5954a48')}</option>
        <option value="normal">{tChrome('k45e118d056')}</option>
        <option value="low">{tChrome('ka124947cbd')}</option>
      </select>

      <select
        className="inv-msg-filters__select"
        value={filters.status}
        onChange={(e) =>
          onFiltersChange({
            status: e.target.value as ConversationFilterState['status'],
          })
        }
        aria-label={tChrome('kf43653d7fa')}
      >
        <option value="all">{tChrome('k6405179d24')}</option>
        <option value="active">{tChrome('ka733b809d2')}</option>
        <option value="archived">{tChrome('keddc813f35')}</option>
        <option value="closed">{tChrome('k88d86b7721')}</option>
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
        />{investorChrome(tChrome, "Has attachments")}</label>

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
        aria-label={tChrome('kefe8028c4e')}
      >
        <option value="lastMessageAt-desc">{tChrome('kf5ec7772ca')}</option>
        <option value="lastMessageAt-asc">{tChrome('k6a99c65c33')}</option>
        <option value="subject-asc">{tChrome('k301e1a06ad')}</option>
        <option value="priority-asc">{tChrome('k886cbff9d9')}</option>
        <option value="unreadCount-desc">{tChrome('kaf99f3225b')}</option>
      </select>
    </div>
  );
}
