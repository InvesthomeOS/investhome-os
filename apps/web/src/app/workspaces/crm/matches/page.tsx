import { CrmMatchesWorkspace } from './_components/crm-matches-workspace';
import { makeMatchesPreview } from './matches-demo-data';
import './matches.css';

/**
 * Canonical CRM Matches route.
 * Presentation uses typed local fixtures until a live matching API is wired.
 */
export default function CrmMatchesPage() {
  const preview = makeMatchesPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-matches-page">
      <CrmMatchesWorkspace preview={preview} />
    </main>
  );
}
