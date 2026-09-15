import { CrmPipelineWorkspace } from '../_components/g2/crm-pipeline-workspace';
import '../opportunities-foundation.css';

export default function CrmPipelinePage() {
  return (
    <main className="dashboard crm-module-shell crm-g2-page crm-pipeline-page" data-testid="crm-g2-pipeline-page">
      <CrmPipelineWorkspace />
    </main>
  );
}
