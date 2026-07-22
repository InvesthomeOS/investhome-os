import { CrmModuleShell } from '../_components/crm-module-shell';
import { CommunicationWorkspace } from './_components/communication-workspace';

export default function CrmCommunicationPage() {
  return (
    <CrmModuleShell
      titleKey="modules.communication.title"
      descriptionKey="modules.communication.description"
    >
      <CommunicationWorkspace />
    </CrmModuleShell>
  );
}
