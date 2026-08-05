import { AdminSystemLogsWorkspace } from '../_components/admin-system-logs-workspace';
import { makeSystemLogsPreview } from '../admin-subpages-demo-data';

export default function AdminSystemLogsPage() {
  const preview = makeSystemLogsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="admin-system-logs-page">
      <AdminSystemLogsWorkspace preview={preview} />
    </main>
  );
}
