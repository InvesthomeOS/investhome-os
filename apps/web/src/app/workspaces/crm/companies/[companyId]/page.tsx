import { CrmModuleShell } from '../../_components/crm-module-shell';
import { CrmCompanyDetailView } from '../../_components/crm-company-detail';

type PageProps = {
  params: Promise<{ companyId: string }>;
};

export default async function CrmCompanyDetailPage({ params }: PageProps) {
  const { companyId } = await params;
  return (
    <CrmModuleShell titleKey="modules.companies.title" descriptionKey="modules.companies.description">
      <CrmCompanyDetailView companyId={companyId} />
    </CrmModuleShell>
  );
}
