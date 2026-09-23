import { CrmLeadsLiveWorkspace } from './_components/crm-leads-live-workspace';
import '../tasks/tasks.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import './leads.css';

export default function CrmLeadsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-leads-page">
      <CrmLeadsLiveWorkspace />
    </main>
  );
}
