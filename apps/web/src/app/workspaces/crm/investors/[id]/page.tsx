import { ContactVerificationDetail } from '../../contacts/_components/contact-verification-detail';

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function CrmInvestorDetailPage({ params }: PageProps) {
  const { id } = await params;
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-investor-detail-page">
      <ContactVerificationDetail contactId={id} />
    </main>
  );
}
