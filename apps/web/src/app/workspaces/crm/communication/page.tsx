import { CrmCommunicationHistoryWorkspace } from './_components/crm-communication-history-workspace';

export default function CrmCommunicationPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-communication-page">
      <CrmCommunicationHistoryWorkspace />
    </main>
  );
}
