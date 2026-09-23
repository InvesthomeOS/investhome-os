import { CrmTagsLiveWorkspace } from './_components/crm-tags-live-workspace';
import '../tasks/tasks.css';
import './tags.css';

/** Canonical CRM Tags route — live CrmTag rows only, no fixture tags. */
export default function CrmTagsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tags-page">
      <CrmTagsLiveWorkspace />
    </main>
  );
}
