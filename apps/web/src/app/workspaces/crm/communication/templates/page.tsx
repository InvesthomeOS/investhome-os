import { CrmModuleShell } from '../../_components/crm-module-shell';
import { TemplatesView } from '../_components/templates-view';

export default function CommunicationTemplatesPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.templates.subtitle">
      <TemplatesView />
    </CrmModuleShell>
  );
}
