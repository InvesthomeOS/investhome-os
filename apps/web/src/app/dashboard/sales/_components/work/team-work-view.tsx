'use client';

import { useTranslations } from 'next-intl';

import { EmptyState, LoadingState } from '@investhome/ui';

import type { WorkItem } from '@/lib/api/work-items';
import { useWorkItemLabels } from '@/lib/i18n/work-item-labels';

interface TeamWorkViewProps {
  items: WorkItem[];
  loading: boolean;
}

export function TeamWorkView({ items, loading }: TeamWorkViewProps) {
  const t = useTranslations('work');
  const { getTypeLabel, getStatusLabel } = useWorkItemLabels();

  if (loading) return <LoadingState label={t('loading')} />;
  if (items.length === 0) return <EmptyState title={t('team.emptyTitle')} description={t('team.emptyDescription')} />;

  const byUser = items.reduce<Record<string, WorkItem[]>>((acc, item) => {
    const key = item.assigned_user_id ?? t('team.unassigned');
    acc[key] = acc[key] ?? [];
    acc[key].push(item);
    return acc;
  }, {});

  return (
    <div className="sales-work-team">
      {Object.entries(byUser).map(([userId, userItems]) => (
        <section key={userId} className="sales-work-team__group">
          <h3>{userId === t('team.unassigned') ? t('team.unassigned') : userId.slice(0, 8)}</h3>
          <ul>
            {userItems.map((item) => (
              <li key={item.id}>
                <strong>{item.title}</strong>
                <span>{getTypeLabel(item.work_item_type)} · {getStatusLabel(item.effective_status ?? item.status)}</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
