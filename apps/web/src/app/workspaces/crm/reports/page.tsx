import { CrmReportsWorkspace } from './_components/crm-reports-workspace';
import { makeReportsPreview } from './reports-demo-data';
import './reports.css';

/**
 * Canonical CRM Reports route.
 * Presentation uses typed local fixtures until a live reporting API is wired
 * into the Dashboard Freeze foundation workspace.
 */
export default function CrmReportsPage() {
  const preview = makeReportsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-reports-page">
      <CrmReportsWorkspace preview={preview} />
    </main>
  );
}
