import { redirect } from 'next/navigation';

interface ProjectDetailIndexProps {
  params: Promise<{ projectId: string }>;
}

export default async function ProjectDetailIndexPage({ params }: ProjectDetailIndexProps) {
  const { projectId } = await params;
  redirect(`/dashboard/projects/${projectId}/overview`);
}
