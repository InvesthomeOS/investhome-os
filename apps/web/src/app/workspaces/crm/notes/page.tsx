import { NotesDsWorkspace } from './_components/ds/notes-ds-workspace';

/**
 * Canonical Notes nav route (`/workspaces/crm/notes`).
 * Contacts/Communication/Timeline-quality DS — CRM knowledge workspace (UI only).
 */
export default function CrmNotesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-notes-page">
      <NotesDsWorkspace />
    </main>
  );
}
