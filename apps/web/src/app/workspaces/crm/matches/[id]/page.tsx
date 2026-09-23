import { CrmMatchesLiveWorkspace } from '../_components/crm-matches-live-workspace';
import '../../tasks/tasks.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import '../../leads/leads.css';
import '../matches-live.css';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmMatchDetailPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-matches-page">
      <CrmMatchesLiveWorkspace initialId={id} />
    </main>
  );
}
