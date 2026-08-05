import { CrmTasksWorkspace } from './_components/crm-tasks-workspace';
import { makeTasksPreview } from './tasks-demo-data';
import './tasks.css';

/**
 * Canonical CRM Tasks route.
 * Presentation uses typed local fixtures until a live tasks API is re-wired
 * into the Dashboard Freeze foundation workspace.
 */
export default function CrmTasksPage() {
  const preview = makeTasksPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tasks-page">
      <CrmTasksWorkspace preview={preview} />
    </main>
  );
}
