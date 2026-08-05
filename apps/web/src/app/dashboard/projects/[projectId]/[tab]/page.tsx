import { notFound, redirect } from 'next/navigation';

import { ProjectsDetailDsWorkspace } from '../../_components/ds/projects-detail-ds-workspace';
import {
  isProjectDetailTab,
  projectDetailHref,
  resolveProjectDetailDsTab,
} from '@/lib/projects/project-detail-tabs';

interface ProjectDetailTabPageProps {
  params: Promise<{ projectId: string; tab: string }>;
}

export default async function ProjectDetailTabPage({ params }: ProjectDetailTabPageProps) {
  const { projectId, tab } = await params;
  if (!isProjectDetailTab(tab)) {
    notFound();
  }

  const resolved = resolveProjectDetailDsTab(tab);
  if (!resolved) {
    notFound();
  }

  if (resolved !== tab) {
    redirect(projectDetailHref(projectId, resolved));
  }

  return <ProjectsDetailDsWorkspace projectId={projectId} tab={resolved} />;
}
