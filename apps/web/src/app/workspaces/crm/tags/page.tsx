import { CrmModuleShell } from '../_components/crm-module-shell';

export default function CrmTagsPage() {
  return (
    <CrmModuleShell
      titleKey="modules.tags.title"
      descriptionKey="modules.tags.description"
      initializing
    />
  );
}
