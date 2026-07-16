'use client';

import { Breadcrumbs } from './breadcrumbs';
import { DashboardHeaderActions } from './dashboard-header-actions';

export function AppHeader() {
  return (
    <header className="app-header">
      <Breadcrumbs />
      <DashboardHeaderActions />
    </header>
  );
}
