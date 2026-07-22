import { CrmModuleShell } from '../../_components/crm-module-shell';
import { CrmCompanyImportWizard } from '../../_components/crm-company-import-wizard';

export default function CrmCompanyImportPage() {
  return (
    <CrmModuleShell titleKey="companies.import.title" descriptionKey="companies.import.pageDescription">
      <CrmCompanyImportWizard />
    </CrmModuleShell>
  );
}
