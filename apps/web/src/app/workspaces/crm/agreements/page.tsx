import { AgreementsWorkspace } from './_components/agreements-workspace';

export default function CrmAgreementsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-agreements-page">
      <AgreementsWorkspace />
    </main>
  );
}
