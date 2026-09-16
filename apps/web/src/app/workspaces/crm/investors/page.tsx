import { CrmInvestorsWorkspace } from './_components/crm-investors-workspace';
import '../people/people.css';

/**
 * CRM Investors workspace — canonical CrmContact rows with real agreement/investment relationships.
 */
export default function CrmInvestorsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-investors-page">
      <CrmInvestorsWorkspace />
    </main>
  );
}
