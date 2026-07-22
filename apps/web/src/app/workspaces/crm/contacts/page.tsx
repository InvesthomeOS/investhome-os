import { ContactsWorkspace } from './_components/contacts-workspace';
import { CrmModuleShell } from '../_components/crm-module-shell';

export default function CrmContactsPage() {
  return (
    <CrmModuleShell titleKey="modules.contacts.title" descriptionKey="modules.contacts.description">
      <ContactsWorkspace />
    </CrmModuleShell>
  );
}
