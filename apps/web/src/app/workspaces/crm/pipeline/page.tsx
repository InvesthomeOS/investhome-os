import { CrmPipelineLiveWorkspace } from './_components/crm-pipeline-live-workspace';
import '../tasks/tasks.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import '../leads/leads.css';
import './pipeline.css';

export default function CrmPipelinePage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-pipeline-page">
      <CrmPipelineLiveWorkspace />
    </main>
  );
}
