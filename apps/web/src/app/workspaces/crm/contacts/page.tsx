import { ContactsLiveVerificationWorkspace } from './_components/contacts-live-verification-workspace';

/**
 * Canonical Contacts nav route (`/workspaces/crm/contacts`).
 * Projects-quality DS presentation — detail routes under `/contacts/[contactId]` unchanged.
 */
export default function CrmContactsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-contacts-page">
      <ContactsLiveVerificationWorkspace />
    </main>
  );
}
