'use client';

import { EmptyState, LoadingState, StatusChip } from '@investhome/ui';
import { useLocale, useTranslations } from 'next-intl';

import type { WorkItem } from '@/lib/api/work-items';
import { useWorkItemLabels } from '@/lib/i18n/work-item-labels';

interface WorkItemListProps {
  items: WorkItem[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (item: WorkItem) => void;
}

function formatDate(value: string | null, locale: string) {
  if (!value) return '—';
  return new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

export function WorkItemList({ items, loading, selectedId, onSelect }: WorkItemListProps) {
  const t = useTranslations('work');
  const locale = useLocale();
  const { getTypeLabel, getStatusLabel, getPriorityLabel } = useWorkItemLabels();

  if (loading) return <LoadingState label={t('loading')} />;
  if (items.length === 0) return <EmptyState title={t('empty.title')} description={t('empty.description')} />;

  return (
    <div className="sales-work-list">
      <table className="sales-work-list__table">
        <thead>
          <tr>
            <th>{t('columns.title')}</th>
            <th>{t('columns.type')}</th>
            <th>{t('columns.status')}</th>
            <th>{t('columns.priority')}</th>
            <th>{t('columns.due')}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const status = item.effective_status ?? item.status;
            return (
              <tr
                key={item.id}
                className={selectedId === item.id ? 'sales-work-list__row--selected' : undefined}
                onClick={() => onSelect(item)}
              >
                <td>
                  {item.is_private && <span aria-hidden="true">🔒 </span>}
                  {item.title}
                </td>
                <td>{getTypeLabel(item.work_item_type)}</td>
                <td>
                  <StatusChip tone={status === 'overdue' ? 'danger' : 'default'}>{getStatusLabel(status)}</StatusChip>
                </td>
                <td>{getPriorityLabel(item.priority)}</td>
                <td>{formatDate(item.due_at, locale)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
