import { InvestorsWorkspace } from './_components/investors-workspace';
import '../contacts/_components/people-workspace.css';

export default function CrmInvestorsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-investors-page">
      <InvestorsWorkspace />
    </main>
  );
}
