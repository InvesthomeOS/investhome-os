'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';
import { WorkspaceHeaderUser } from '@/components/shell/workspace-header-user';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { AiGlobalButton } from '@/components/ai/ai-global-button';

import { GlobalSearchTrigger } from './global-search-trigger';
import { LanguageSelector } from './language-selector';
import { NotificationBell } from './notification-bell';
import { ThemeToggle } from './theme-toggle';

export function DashboardHeaderActions() {
  const tHome = useTranslations('home');
  const { user } = useAuth();
  const canCreateLead = user
    ? hasPermission(user, 'sales', 'create') || hasPermission(user, 'leads', 'create')
    : false;

  return (
    <div className="dashboard__header-actions app-header__actions">
      <GlobalSearchTrigger />
      <AiGlobalButton />
      {canCreateLead && (
        <Link href={'/dashboard/sales' as Route} className="app-header__quick">
          <IhIcon name="plus" size={15} />
          {tHome('quickActions.newLead')}
        </Link>
      )}
      <ThemeToggle />
      <LanguageSelector />
      <NotificationBell />
      <WorkspaceHeaderUser />
    </div>
  );
}
