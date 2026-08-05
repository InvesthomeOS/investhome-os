import { CrmMatchDetailView } from '../_components/crm-match-detail';
import '../matches.css';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmMatchDetailPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-match-detail-page">
      <CrmMatchDetailView matchId={id} />
    </main>
  );
}
