import { CrmModuleShell } from '../../_components/crm-module-shell';
import { AnalyticsView } from '../_components/analytics-view';

export default function CommunicationAnalyticsPage() {
  return (
    <CrmModuleShell titleKey="modules.communication.title" descriptionKey="communication.analytics.subtitle">
      <AnalyticsView />
    </CrmModuleShell>
  );
}
