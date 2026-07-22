import { DocumentDetailPage } from '../_components/document-detail-page';

interface DocumentDetailRouteProps {
  params: Promise<{ id: string }>;
}

export default async function DocumentDetailRoute({ params }: DocumentDetailRouteProps) {
  const { id } = await params;
  return <DocumentDetailPage documentId={id} />;
}
