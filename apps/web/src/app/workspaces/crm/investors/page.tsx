import { InvestorsWorkspace } from './_components/investors-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import './investors-ops.css';

export default function CrmInvestorsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-investors-page">
      <InvestorsWorkspace />
    </main>
  );
}
