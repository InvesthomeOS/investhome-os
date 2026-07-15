import { DesignDetailView } from '../_components/design-detail-view';

interface DesignDetailPageProps {
  params: Promise<{ id: string }>;
}

export default async function DesignDetailPage({ params }: DesignDetailPageProps) {
  const { id } = await params;
  return <DesignDetailView designId={id} />;
}
