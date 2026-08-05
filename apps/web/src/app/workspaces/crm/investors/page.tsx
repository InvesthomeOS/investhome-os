import { CrmInvestorsWorkspace } from './_components/crm-investors-workspace';
import { makeInvestorsPreview } from './investors-demo-data';
import '../people/people.css';

/**
 * CRM Investors workspace — People foundation adapted for investor portfolio.
 */
export default function CrmInvestorsPage() {
  const preview = makeInvestorsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-investors-page">
      <CrmInvestorsWorkspace preview={preview} />
    </main>
  );
}
