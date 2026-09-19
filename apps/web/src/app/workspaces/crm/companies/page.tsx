import { CrmCompaniesWorkspace } from './_components/crm-companies-workspace';
import './companies.css';

/**
 * Canonical CRM Companies route — live crm_companies list.
 */
export default function CrmCompaniesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-companies-page">
      <CrmCompaniesWorkspace />
    </main>
  );
}
