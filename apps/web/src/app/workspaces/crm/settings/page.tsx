import { CrmSettingsLiveWorkspace } from './_components/crm-settings-live-workspace';
import './settings-ops.css';

/**
 * Canonical CRM Settings route.
 * Live company, communication, provider, and security reads only.
 * Connection state is shown only when a backend confirms it.
 */
export default function CrmSettingsPage() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-settings-page">
      <CrmSettingsLiveWorkspace />
    </main>
  );
}
