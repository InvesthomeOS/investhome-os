import { CrmPeopleWorkspace } from './_components/crm-people-workspace';
import { makePeoplePreview } from './people-demo-data';
import './people.css';

/**
 * Canonical CRM People (Kişiler) route.
 * Presentation uses typed local fixtures until a live contacts API is re-wired
 * into the Dashboard Freeze foundation workspace.
 */
export default function CrmPeoplePage() {
  const preview = makePeoplePreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-people-page">
      <CrmPeopleWorkspace preview={preview} />
    </main>
  );
}
