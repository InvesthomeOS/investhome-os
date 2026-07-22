import { CrmModuleShell } from '../_components/crm-module-shell';

export default function CrmReportsPage() {
  return (
    <CrmModuleShell
      titleKey="modules.reports.title"
      descriptionKey="modules.reports.description"
      initializing
    />
  );
}
