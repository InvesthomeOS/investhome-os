import { AdminIntegrationsWorkspace } from '../_components/admin-integrations-workspace';
import { makeAdminIntegrationsPreview } from '../admin-subpages-demo-data';

export default function AdminIntegrationsPage() {
  const preview = makeAdminIntegrationsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="admin-integrations-page">
      <AdminIntegrationsWorkspace preview={preview} />
    </main>
  );
}
