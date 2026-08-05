import { CrmPersonDetailView } from '../_components/crm-person-detail';
import '../people.css';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmPersonDetailPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-person-detail-page">
      <CrmPersonDetailView personId={id} />
    </main>
  );
}
