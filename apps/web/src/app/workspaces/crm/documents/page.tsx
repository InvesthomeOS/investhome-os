import { CrmDocumentsLiveWorkspace } from './_components/crm-documents-live-workspace';
import '../tasks/tasks.css';
import '../communication/communication.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import './documents.css';

export default function CrmDocumentsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-documents-page">
      <CrmDocumentsLiveWorkspace />
    </main>
  );
}
