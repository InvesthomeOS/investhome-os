import { RelationshipDetailView } from '../_components/relationship-detail-view';

type Props = { params: Promise<{ relationshipId: string }> };

export default async function CrmRelationshipDetailPage({ params }: Props) {
  const { relationshipId } = await params;
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-relationship-detail-page">
      <RelationshipDetailView relationshipId={relationshipId} />
    </main>
  );
}
