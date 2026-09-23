import { Suspense } from 'react';

import { PeopleWorkspace } from './_components/people-workspace';

/**
 * Canonical Contacts nav route (`/workspaces/crm/contacts`).
 * Operational people table — detail routes under `/contacts/[contactId]` unchanged.
 */
export default function CrmContactsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-contacts-page">
      <Suspense fallback={null}>
        <PeopleWorkspace />
      </Suspense>
    </main>
  );
}
