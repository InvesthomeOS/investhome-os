'use client';

import { DashboardHeaderActions } from './dashboard-header-actions';
import { WorkspaceTitle } from './workspace-title';

export function AppHeader() {
  return (
    <header className="app-header">
      <WorkspaceTitle />
      <DashboardHeaderActions />
    </header>
  );
}
