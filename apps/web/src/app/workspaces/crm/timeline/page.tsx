import { TimelineDsWorkspace } from './_components/ds/timeline-ds-workspace';

/**
 * Canonical Timeline nav route (`/workspaces/crm/timeline`).
 * Operational feed from live CRM records (activities, purchases, documents).
 */
export default function CrmTimelinePage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-timeline-page">
      <TimelineDsWorkspace />
    </main>
  );
}
