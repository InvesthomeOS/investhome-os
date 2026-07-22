import { CrmLeadsWorkspace } from '../_components/g2/crm-leads-workspace';

export default function CrmLeadsPage() {
  return (
    <main className="dashboard crm-module-shell crm-g2-page" data-testid="crm-g2-leads-page">
      <CrmLeadsWorkspace />
    </main>
  );
}
