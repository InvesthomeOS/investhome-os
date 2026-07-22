import { notFound } from 'next/navigation';

import { ProjectDetailWorkspace } from '../../_components/project-detail-workspace';
import { isProjectDetailTab } from '@/lib/projects/project-detail-tabs';

interface ProjectDetailTabPageProps {
  params: Promise<{ projectId: string; tab: string }>;
}

export default async function ProjectDetailTabPage({ params }: ProjectDetailTabPageProps) {
  const { projectId, tab } = await params;
  if (!isProjectDetailTab(tab)) {
    notFound();
  }
  return <ProjectDetailWorkspace projectId={projectId} tab={tab} />;
}
