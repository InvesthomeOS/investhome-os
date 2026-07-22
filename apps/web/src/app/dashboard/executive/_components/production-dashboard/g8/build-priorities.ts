import type { Route } from 'next';

import {
  moduleHref,
  type ApprovalItem,
  type AttentionItem,
  type DeadlineItem,
} from '@/lib/api/executive';

import { sortAttentionByUrgency as sortAtt } from '../../command-center/build-metrics';

export type PrioritySeverity = 'critical' | 'warning' | 'information';

export interface G8PriorityItem {
  id: string;
  title: string;
  reason: string;
  severity: PrioritySeverity;
  sourceWorkspace: string;
  relatedLabel: string | null;
  dueDate: string | null;
  owner: string | null;
  recommendedAction: string | null;
  href: Route;
}

/** Honest ranking: severity → due date → age. No fabricated scores. */
export function buildTodaysPriorities(input: {
  attention: AttentionItem[];
  approvals: ApprovalItem[];
  deadlines: DeadlineItem[];
  resolveAttentionTitle: (item: AttentionItem) => string;
  resolveAttentionReason: (item: AttentionItem) => string;
  resolveApprovalTitle: (item: ApprovalItem) => string;
  workspaceLabel: (module: string) => string;
  max?: number;
}): G8PriorityItem[] {
  const max = input.max ?? 8;
  const items: G8PriorityItem[] = [];

  for (const item of sortAtt(input.attention)) {
    items.push({
      id: `att-${item.entity_type}-${item.entity_id}-${item.title_key}`,
      title: input.resolveAttentionTitle(item),
      reason: input.resolveAttentionReason(item),
      severity: item.severity,
      sourceWorkspace: input.workspaceLabel(item.link_module),
      relatedLabel: item.related_label,
      dueDate: item.due_date,
      owner: typeof item.metadata.owner === 'string' ? item.metadata.owner : null,
      recommendedAction: typeof item.metadata.action === 'string' ? item.metadata.action : null,
      href: moduleHref(item.link_module, item.link_query),
    });
  }

  for (const item of input.approvals) {
    const ageBoost = (item.age_days ?? 0) >= 3 ? 'warning' : 'information';
    items.push({
      id: `appr-${item.approval_type}-${item.entity_id}`,
      title: input.resolveApprovalTitle(item),
      reason: item.related_label ?? item.approval_type,
      severity: ageBoost,
      sourceWorkspace: input.workspaceLabel(item.link_module),
      relatedLabel: item.related_label,
      dueDate: item.submitted_at,
      owner: null,
      recommendedAction: null,
      href: moduleHref(item.link_module, item.link_query),
    });
  }

  for (const item of input.deadlines.filter((d) => d.window === 'overdue' || d.window === 'next_7_days')) {
    items.push({
      id: `dl-${item.entity_type}-${item.entity_id}-${item.due_date}`,
      title: item.title,
      reason: item.related_label ?? item.deadline_type,
      severity: item.window === 'overdue' ? 'critical' : 'warning',
      sourceWorkspace: input.workspaceLabel(item.link_module),
      relatedLabel: item.related_label,
      dueDate: item.due_date,
      owner: null,
      recommendedAction: null,
      href: moduleHref(item.link_module, item.link_query),
    });
  }

  const rank: Record<PrioritySeverity, number> = {
    critical: 0,
    warning: 1,
    information: 2,
  };

  const seen = new Set<string>();
  return items
    .sort((a, b) => {
      const sev = rank[a.severity] - rank[b.severity];
      if (sev !== 0) return sev;
      const aDue = a.dueDate ? new Date(a.dueDate).getTime() : Number.POSITIVE_INFINITY;
      const bDue = b.dueDate ? new Date(b.dueDate).getTime() : Number.POSITIVE_INFINITY;
      return aDue - bDue;
    })
    .filter((item) => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    })
    .slice(0, max);
}
