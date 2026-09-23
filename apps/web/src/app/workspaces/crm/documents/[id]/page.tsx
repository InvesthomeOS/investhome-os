import { CrmDocumentDetailView } from '../_components/crm-document-detail';
import '../documents.css';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmDocumentDetailPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-document-detail-page">
      <CrmDocumentDetailView documentId={id} />
    </main>
  );
}
