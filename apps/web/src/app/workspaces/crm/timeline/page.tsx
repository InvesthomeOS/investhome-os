import { TimelineDsWorkspace } from './_components/ds/timeline-ds-workspace';

/**
 * Canonical Timeline nav route (`/workspaces/crm/timeline`).
 * Contacts/Projects/Communication-quality DS — command timeline (presentation only).
 */
export default function CrmTimelinePage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-timeline-page">
      <TimelineDsWorkspace />
    </main>
  );
}
