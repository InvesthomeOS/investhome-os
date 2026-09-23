'use client';

import { CrmPanoLiveWorkspace } from '../dashboard/_components/crm-pano-live-workspace';
import '../reports/reports.css';
import '../dashboard/pano.css';

export function CrmDashboard() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-dashboard-page">
      <CrmPanoLiveWorkspace />
    </main>
  );
}
