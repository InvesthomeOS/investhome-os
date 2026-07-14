'use client';

import { LanguageSelector } from './language-selector';
import { OperationalStatus } from './operational-status';

export function DashboardHeaderActions() {
  return (
    <div className="dashboard__header-actions">
      <LanguageSelector />
      <OperationalStatus />
    </div>
  );
}
