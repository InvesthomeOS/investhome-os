import { WorkflowDetailWorkspace } from '../../_components/workflow-detail';

export default async function AutomationWorkflowDetailPage({
  params,
}: {
  params: Promise<{ workflowId: string }>;
}) {
  const { workflowId } = await params;
  return <WorkflowDetailWorkspace workflowId={decodeURIComponent(workflowId)} />;
}
