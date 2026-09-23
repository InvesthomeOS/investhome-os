import { ContactImportWizard } from '../_components/contact-import-wizard';
import { CrmModuleShell } from '../../_components/crm-module-shell';

export default function ContactImportPage() {
  return (
    <CrmModuleShell titleKey="contacts.import.title" descriptionKey="contacts.import.subtitle">
      <ContactImportWizard />
    </CrmModuleShell>
  );
}
