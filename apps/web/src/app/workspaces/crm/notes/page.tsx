import { CrmNotesWorkspace } from './_components/crm-notes-workspace';
import '../tasks/tasks.css';
import './notes.css';

export default function CrmNotesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-notes-page">
      <CrmNotesWorkspace />
    </main>
  );
}
