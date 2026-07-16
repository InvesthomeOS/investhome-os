import { LeadDetailPage } from '../_components/lead-detail-page';

interface LeadDetailRouteProps {
  params: Promise<{ id: string }>;
}

export default async function LeadDetailRoute({ params }: LeadDetailRouteProps) {
  const { id } = await params;
  return <LeadDetailPage leadId={id} />;
}
