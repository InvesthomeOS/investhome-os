import { CrmModuleShell } from '../../_components/crm-module-shell';
import { SignaturesView } from '../_components/signatures-view';

export default function CommunicationSignaturesPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.signatures.subtitle">
      <SignaturesView />
    </CrmModuleShell>
  );
}
