import { CrmSettingsWorkspace } from './_components/crm-settings-workspace';
import { makeSettingsPreview } from './settings-demo-data';
import './settings.css';

/**
 * Canonical CRM Settings route.
 * Presentation uses typed local fixtures until live settings services are wired
 * into the Dashboard Freeze System Control Center foundation.
 */
export default function CrmSettingsPage() {
  const preview = makeSettingsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-settings-page">
      <CrmSettingsWorkspace preview={preview} />
    </main>
  );
}
