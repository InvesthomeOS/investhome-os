import { CrmModuleShell } from '../../_components/crm-module-shell';
import { CommunicationAccountsView } from '../_components/communication-accounts-view';
import { Suspense } from 'react';

export default function CommunicationAccountsPage() {
  return (
    <CrmModuleShell
      titleKey="settings.communicationAccounts.title"
      descriptionKey="settings.communicationAccounts.subtitle"
    >
      <Suspense fallback={null}>
        <CommunicationAccountsView />
      </Suspense>
    </CrmModuleShell>
  );
}
