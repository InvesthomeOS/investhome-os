import { CompaniesWorkspace } from './_components/companies-workspace';
import './companies.css';

export default function CrmCompaniesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-companies-page">
      <CompaniesWorkspace />
    </main>
  );
}
