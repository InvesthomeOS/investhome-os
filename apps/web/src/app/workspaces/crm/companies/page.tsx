import { CrmCompaniesWorkspace } from './_components/crm-companies-workspace';
import { makeCompaniesPreview } from './companies-demo-data';
import './companies.css';

/**
 * Canonical CRM Companies route.
 * Presentation uses typed local fixtures until a live companies API is re-wired
 * into the Dashboard Freeze foundation workspace.
 */
export default function CrmCompaniesPage() {
  const preview = makeCompaniesPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-companies-page">
      <CrmCompaniesWorkspace preview={preview} />
    </main>
  );
}
