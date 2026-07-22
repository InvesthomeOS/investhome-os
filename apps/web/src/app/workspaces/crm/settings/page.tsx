import { CrmModuleShell } from '../_components/crm-module-shell';

export default function CrmSettingsPage() {
  return (
    <CrmModuleShell
      titleKey="modules.settings.title"
      descriptionKey="modules.settings.description"
      initializing
    />
  );
}
