import { CrmCalendarWorkspace } from './_components/crm-calendar-workspace';
import { makeCalendarPreview } from './calendar-demo-data';
import './calendar.css';

/**
 * Canonical CRM Calendar route.
 * Presentation uses typed local fixtures until a live calendar API is wired
 * into the Dashboard Freeze foundation workspace.
 */
export default function CrmCalendarPage() {
  const preview = makeCalendarPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-calendar-page">
      <CrmCalendarWorkspace preview={preview} />
    </main>
  );
}
