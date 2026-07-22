'use client';

import { NotificationBell } from '@/app/dashboard/_components/notification-bell';
import { LanguageSelector } from '@/app/dashboard/_components/language-selector';
import { ThemeToggle } from '@/app/dashboard/_components/theme-toggle';
import { WorkspaceHeaderUser } from '@/components/shell/workspace-header-user';

import { CompanyBreadcrumbs } from './company-breadcrumbs';
import { CompanySearchTrigger } from './company-search-trigger';

export function CompanyHeader() {
  return (
    <header className="app-header">
      <div className="app-header__left">
        <CompanyBreadcrumbs />
      </div>
      <div className="dashboard__header-actions app-header__actions">
        <CompanySearchTrigger />
        <ThemeToggle />
        <LanguageSelector />
        <NotificationBell />
        <WorkspaceHeaderUser />
      </div>
    </header>
  );
}
