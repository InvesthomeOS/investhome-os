import { CrmModuleShell } from '../_components/crm-module-shell';

export default function CrmFilesPage() {
  return (
    <CrmModuleShell
      titleKey="modules.files.title"
      descriptionKey="modules.files.description"
      initializing
    />
  );
}
