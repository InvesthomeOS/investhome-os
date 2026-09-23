import { RelationshipNetworkView } from '../_components/relationship-network-view';

export default function CrmRelationshipsNetworkPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-relationships-network-page">
      <RelationshipNetworkView />
    </main>
  );
}
