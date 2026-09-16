import { CrmActivitiesWorkspace } from './_components/crm-activities-workspace';
import './activities.css';

export default function CrmActivitiesPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-activities-page">
      <CrmActivitiesWorkspace />
    </main>
  );
}
