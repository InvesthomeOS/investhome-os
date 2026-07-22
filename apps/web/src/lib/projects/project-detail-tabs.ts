import type { ProjectDetailTabKey } from '@/lib/api/projects';

export const PROJECT_DETAIL_TABS: readonly ProjectDetailTabKey[] = [
  'overview',
  'financials',
  'schedule',
  'construction',
  'units',
  'sales',
  'leasing',
  'investors',
  'documents',
  'team',
  'activity',
] as const;

export function isProjectDetailTab(value: string): value is ProjectDetailTabKey {
  return (PROJECT_DETAIL_TABS as readonly string[]).includes(value);
}

export function projectDetailHref(projectId: string, tab: ProjectDetailTabKey = 'overview'): string {
  return `/dashboard/projects/${projectId}/${tab}`;
}
