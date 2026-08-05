import { CommunicationDsWorkspace } from './_components/ds/communication-ds-workspace';

/**
 * Canonical Communication nav route (`/workspaces/crm/communication`).
 * Contacts/Projects-quality DS — operational communication workspace (no KPI strip).
 */
export default function CrmCommunicationPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-communication-page">
      <CommunicationDsWorkspace />
    </main>
  );
}
