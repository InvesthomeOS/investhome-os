import { CrmDocumentsLiveWorkspace } from './_components/crm-documents-live-workspace';

export default function CrmDocumentsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-documents-page">
      <CrmDocumentsLiveWorkspace />
    </main>
  );
}
