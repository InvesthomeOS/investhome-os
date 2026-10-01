import { CrmMatchesLiveWorkspace } from './_components/crm-matches-live-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import './matches-ops.css';

export default function CrmMatchesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-matches-page">
      <CrmMatchesLiveWorkspace />
    </main>
  );
}
