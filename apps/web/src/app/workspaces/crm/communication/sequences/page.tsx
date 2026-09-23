import { CrmModuleShell } from '../../_components/crm-module-shell';
import { SequencesView } from '../_components/sequences-view';

export default function CommunicationSequencesPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.sequences.subtitle">
      <SequencesView />
    </CrmModuleShell>
  );
}
