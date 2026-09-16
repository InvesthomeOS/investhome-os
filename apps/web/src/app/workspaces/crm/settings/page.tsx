import { CrmSettingsWorkspace } from './_components/crm-settings-workspace';
import { makeSettingsPreview } from './settings-demo-data';
import './settings.css';

/**
 * Canonical CRM Settings route.
 * Integration connection state is shown only when a backend confirms it.
 */
export default function CrmSettingsPage() {
  const preview = makeSettingsPreview();

  return (
    <main className="dashboard crm-module-shell" data-testid="crm-settings-page">
      <CrmSettingsWorkspace preview={preview} />
    </main>
  );
}
