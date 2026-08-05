import { DocumentsDsWorkspace } from './_components/ds/documents-ds-workspace';

/**
 * Canonical CRM Documents route — unified Belgeler workspace (Files merged).
 * Presentation uses typed local fixtures until live document/file APIs are wired.
 */
export default function CrmDocumentsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-documents-page">
      <DocumentsDsWorkspace />
    </main>
  );
}
