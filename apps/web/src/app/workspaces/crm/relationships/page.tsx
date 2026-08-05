import { RelationshipsDsWorkspace } from './_components/ds/relationships-ds-workspace';

/**
 * Canonical Relationships nav route (`/workspaces/crm/relationships`).
 * Contacts-quality DS presentation — network/intelligence/detail routes unchanged.
 */
export default function CrmRelationshipsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-relationships-page">
      <RelationshipsDsWorkspace />
    </main>
  );
}
