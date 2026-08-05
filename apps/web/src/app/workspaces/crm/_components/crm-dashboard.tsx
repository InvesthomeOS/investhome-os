'use client';

import { CrmDashboardDsWorkspace } from '../dashboard/_components/ds/crm-dashboard-ds-workspace';

/**
 * CRM Dashboard — Operational Command Center.
 * Presentation rebuilt on Contacts/Projects DS; shell unchanged via CRM layout.
 */
export function CrmDashboard() {
  return (
    <main className="dashboard crm-module-shell" data-testid="crm-dashboard-page">
      <CrmDashboardDsWorkspace />
    </main>
  );
}
