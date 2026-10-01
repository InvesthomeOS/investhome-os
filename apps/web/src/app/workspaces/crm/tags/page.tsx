import { CrmTagsLiveWorkspace } from './_components/crm-tags-live-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import './tags-ops.css';

/** Canonical CRM Tags route — live CrmTag rows only, no fixture tags. */
export default function CrmTagsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-tags-page">
      <CrmTagsLiveWorkspace />
    </main>
  );
}
