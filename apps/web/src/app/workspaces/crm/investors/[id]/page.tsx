import { CrmPersonDetailView } from '../../people/_components/crm-person-detail';
import '../../people/people.css';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmInvestorDetailPage({ params }: PageProps) {
  const { id } = await params;

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-investor-detail-page">
      <CrmPersonDetailView personId={id} listHref="/workspaces/crm/investors" />
    </main>
  );
}
