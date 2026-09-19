import { SalesDetailPage } from '@/workspaces/crm/contact-card/sales-detail-page';

type SalesPageProps = {
  params: Promise<{ contactId: string; agreementId: string }>;
};

export default async function ContactSalesDetailPage({ params }: SalesPageProps) {
  const { contactId, agreementId } = await params;
  return <SalesDetailPage contactId={contactId} agreementId={agreementId} />;
}
