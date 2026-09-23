import { CrmModuleShell } from '../../_components/crm-module-shell';
import { MeetingsView } from '../_components/meetings-view';

export default function CommunicationMeetingsPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.meetings.subtitle">
      <MeetingsView />
    </CrmModuleShell>
  );
}
