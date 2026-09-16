import { CrmReportsLiveWorkspace } from './_components/crm-reports-live-workspace';
import './reports.css';

export default function CrmReportsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-reports-page">
      <CrmReportsLiveWorkspace />
    </main>
  );
}
