import { RelationshipCreateWizard } from '../_components/relationship-create-wizard';

export default function CrmRelationshipNewPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-relationships-new-page">
      <RelationshipCreateWizard />
    </main>
  );
}
