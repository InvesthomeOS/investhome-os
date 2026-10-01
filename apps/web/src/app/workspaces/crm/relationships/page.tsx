import { RelationshipsWorkspace } from './_components/relationships-workspace';

export default function CrmRelationshipsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-relationships-page">
      <RelationshipsWorkspace />
    </main>
  );
}
