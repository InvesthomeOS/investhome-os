import type { ProjectDetailDsTab } from '@/app/dashboard/projects/_components/ds/projects-detail-ds-model';
import {
  isProjectDetailDsTab,
  PROJECT_DETAIL_DS_TABS,
  PROJECT_DETAIL_TAB_ALIASES,
  projectDetailDsHref,
  resolveProjectDetailDsTab,
} from '@/app/dashboard/projects/_components/ds/projects-detail-ds-model';

export const PROJECT_DETAIL_TABS = PROJECT_DETAIL_DS_TABS;

export type ProjectDetailTabKey = ProjectDetailDsTab;

export function isProjectDetailTab(value: string): value is ProjectDetailTabKey {
  return isProjectDetailDsTab(value) || value in PROJECT_DETAIL_TAB_ALIASES;
}

export function projectDetailHref(
  projectId: string,
  tab: ProjectDetailTabKey = 'overview',
): string {
  return projectDetailDsHref(projectId, tab);
}

export { resolveProjectDetailDsTab, PROJECT_DETAIL_TAB_ALIASES };
