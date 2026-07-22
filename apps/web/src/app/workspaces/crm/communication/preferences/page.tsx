import { CrmModuleShell } from '../../_components/crm-module-shell';
import { PreferencesView } from '../_components/preferences-view';

export default function CommunicationPreferencesPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.preferences.subtitle">
      <PreferencesView />
    </CrmModuleShell>
  );
}
