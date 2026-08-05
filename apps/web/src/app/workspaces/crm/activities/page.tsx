import { CrmActivitiesWorkspace } from './_components/crm-activities-workspace';
import { makeActivitiesPreview } from './activities-demo-data';
import './activities.css';

/**
 * Canonical CRM Activities route.
 * Presentation uses typed local fixtures until a live activities API is re-wired
 * into the Dashboard Freeze foundation workspace.
 */
export default function CrmActivitiesPage() {
  const preview = makeActivitiesPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-activities-page">
      <CrmActivitiesWorkspace preview={preview} />
    </main>
  );
}
