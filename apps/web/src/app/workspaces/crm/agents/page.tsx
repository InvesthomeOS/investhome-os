import { AgentsWorkspace } from './_components/agents-workspace';

export default function CrmAgentsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-agents-page">
      <AgentsWorkspace />
    </main>
  );
}
