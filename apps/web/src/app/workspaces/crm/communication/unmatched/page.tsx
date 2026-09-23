import { CrmModuleShell } from '../../_components/crm-module-shell';
import { UnmatchedCommunicationsView } from '../_components/unmatched-communications-view';

export default function UnmatchedCommunicationsPage() {
  return (
    <CrmModuleShell
      titleKey="communication.unmatched.title"
      descriptionKey="communication.unmatched.subtitle"
    >
      <UnmatchedCommunicationsView />
    </CrmModuleShell>
  );
}
