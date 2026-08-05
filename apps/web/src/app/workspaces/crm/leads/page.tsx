import { LeadsDsWorkspace } from './_components/ds/leads-ds-workspace';

/**
 * Canonical Leads nav route (`/workspaces/crm/leads`).
 * Contacts/Projects-quality DS presentation — detail routes under `/dashboard/leads/[id]` unchanged.
 */
export default function CrmLeadsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-leads-page">
      <LeadsDsWorkspace />
    </main>
  );
}
