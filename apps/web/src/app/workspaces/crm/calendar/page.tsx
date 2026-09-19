import { CrmCalendarWorkspace } from './_components/crm-calendar-workspace';
import './calendar.css';

export default function CrmCalendarPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-calendar-page">
      <CrmCalendarWorkspace />
    </main>
  );
}
