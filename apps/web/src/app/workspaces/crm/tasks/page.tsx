import { CrmTasksWorkspace } from './_components/crm-tasks-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import './tasks-ops.css';

export default function CrmTasksPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tasks-page">
      <CrmTasksWorkspace />
    </main>
  );
}
