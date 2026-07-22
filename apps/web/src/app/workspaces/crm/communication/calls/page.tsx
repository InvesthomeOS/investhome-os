import { CrmModuleShell } from '../../_components/crm-module-shell';
import { CallsView } from '../_components/calls-view';

export default function CommunicationCallsPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.calls.subtitle">
      <CallsView />
    </CrmModuleShell>
  );
}
