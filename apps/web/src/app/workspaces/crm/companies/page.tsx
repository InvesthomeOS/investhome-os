import { CompaniesWorkspace } from './_components/companies-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import './companies-ops.css';

export default function CrmCompaniesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-companies-page">
      <CompaniesWorkspace />
    </main>
  );
}
