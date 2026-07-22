import { CrmModuleShell } from '../_components/crm-module-shell';
import { CrmCompaniesList } from '../_components/crm-companies-list';

export default function CrmCompaniesPage() {
  return (
    <CrmModuleShell titleKey="modules.companies.title" descriptionKey="modules.companies.description">
      <CrmCompaniesList />
    </CrmModuleShell>
  );
}
