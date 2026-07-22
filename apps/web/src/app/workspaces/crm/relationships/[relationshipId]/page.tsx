import { RelationshipDetailView } from '../_components/relationship-detail-view';

type Props = { params: Promise<{ relationshipId: string }> };

export default async function CrmRelationshipDetailPage({ params }: Props) {
  const { relationshipId } = await params;
  return <RelationshipDetailView relationshipId={relationshipId} />;
}
