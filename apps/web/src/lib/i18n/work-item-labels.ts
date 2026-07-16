import { useTranslations } from 'next-intl';

import type { WorkItemPriority, WorkItemStatus, WorkItemType, WorkViewName } from '@/lib/api/work-items';

export function useWorkItemLabels() {
  const t = useTranslations('work');

  const getTypeLabel = (type: WorkItemType | string) => t(`types.${type}` as never);
  const getStatusLabel = (status: WorkItemStatus | string) => t(`statuses.${status}` as never);
  const getPriorityLabel = (priority: WorkItemPriority | string) => t(`priorities.${priority}` as never);
  const getViewLabel = (view: WorkViewName | string) => t(`views.${view}` as never);

  return {
    getTypeLabel,
    getStatusLabel,
    getPriorityLabel,
    getViewLabel,
    typeOptions: [
      'task', 'call', 'meeting', 'follow_up', 'site_visit', 'proposal_follow_up',
      'reservation_follow_up', 'deposit_follow_up', 'contract_follow_up', 'closing_follow_up', 'other',
    ] as WorkItemType[],
    priorityOptions: ['low', 'medium', 'high', 'urgent'] as WorkItemPriority[],
    viewOptions: [
      'today', 'overdue', 'upcoming', 'meetings', 'calls', 'follow_ups',
      'waiting', 'blocked', 'completed', 'my_work', 'team_work',
    ] as WorkViewName[],
  };
}
