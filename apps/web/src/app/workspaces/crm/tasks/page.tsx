import { CrmTasksWorkspace } from './_components/crm-tasks-workspace';
import './tasks.css';

export default function CrmTasksPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tasks-page">
      <CrmTasksWorkspace />
    </main>
  );
}
