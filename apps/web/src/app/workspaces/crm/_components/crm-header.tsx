'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { NotificationBell } from '@/app/dashboard/_components/notification-bell';
import { LanguageSelector } from '@/app/dashboard/_components/language-selector';
import { ThemeToggle } from '@/app/dashboard/_components/theme-toggle';
import { AiGlobalButton } from '@/components/ai/ai-global-button';
import { WorkspaceHeaderUser } from '@/components/shell/workspace-header-user';

import { useCrmSearchStore } from '@/workspaces/crm/stores/crm-search-store';

import { CrmBreadcrumbs } from './crm-breadcrumbs';
import { CrmSearchPalette, useCrmSearchShortcuts } from '../search/_components/crm-search-palette';

export function CrmHeader() {
  const tCrm = useTranslations('crm');
  const { canRead } = useCrmAccess();
  const { openPalette } = useCrmSearchStore();
  const [shortcut, setShortcut] = useState('Ctrl+K');

  useCrmSearchShortcuts();

  useEffect(() => {
    const isMac = /mac|iphone|ipad|ipod/i.test(navigator.platform || navigator.userAgent);
    setShortcut(isMac ? '⌘K' : 'Ctrl+K');
  }, []);

  return (
    <header className="app-header">
      <div className="app-header__left">
        <CrmBreadcrumbs />
      </div>
      <div className="dashboard__header-actions app-header__actions">
        {canRead && (
          <button type="button" className="global-search-trigger crm-search-trigger" onClick={openPalette}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.5" />
              <path d="M20 20 16.5 16.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span className="global-search-trigger__label">{tCrm('searchTrigger')}</span>
            <kbd className="global-search-trigger__kbd" suppressHydrationWarning>
              {shortcut}
            </kbd>
          </button>
        )}
        <AiGlobalButton />
        <ThemeToggle />
        <LanguageSelector />
        <NotificationBell />
        <WorkspaceHeaderUser />
      </div>
      <CrmSearchPalette />
    </header>
  );
}
