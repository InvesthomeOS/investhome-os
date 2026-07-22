import { CrmModuleShell } from '../_components/crm-module-shell';

export default function CrmDocumentsPage() {
  return (
    <CrmModuleShell
      titleKey="modules.documents.title"
      descriptionKey="modules.documents.description"
      initializing
    />
  );
}
