import { makeCompaniesPreview } from '../companies-demo-data';
import { CrmCompanyFoundationDetail } from '../_components/crm-company-foundation-detail';
import { CrmModuleShell } from '../../_components/crm-module-shell';
import { CrmCompanyDetailView } from '../../_components/crm-company-detail';

type PageProps = {
  params: Promise<{ companyId: string }>;
};

export default async function CrmCompanyDetailPage({ params }: PageProps) {
  const { companyId } = await params;
  const isFoundationId = makeCompaniesPreview().companies.some((row) => row.id === companyId);

  if (isFoundationId) {
    return (
      <main className="dashboard crm-module-shell" data-testid="crm-company-foundation-detail-page">
        <CrmCompanyFoundationDetail companyId={companyId} />
      </main>
    );
  }

  return (
    <CrmModuleShell titleKey="modules.companies.title" descriptionKey="modules.companies.description">
      <CrmCompanyDetailView companyId={companyId} />
    </CrmModuleShell>
  );
}
