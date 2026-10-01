import { CrmCommunicationLiveWorkspace } from './_components/crm-communication-live-workspace';
import '@/workspaces/crm/contact-card/contact-card.css';
import './communication.css';

export default function CrmCommunicationPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-communication-page">
      <CrmCommunicationLiveWorkspace />
    </main>
  );
}
