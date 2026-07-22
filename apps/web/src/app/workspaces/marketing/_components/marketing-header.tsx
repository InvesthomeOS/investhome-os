'use client';

import { useTranslations } from 'next-intl';

import { NotificationBell } from '@/app/dashboard/_components/notification-bell';
import { LanguageSelector } from '@/app/dashboard/_components/language-selector';
import { ThemeToggle } from '@/app/dashboard/_components/theme-toggle';
import { AiGlobalButton } from '@/components/ai/ai-global-button';
import { WorkspaceHeaderUser } from '@/components/shell/workspace-header-user';

export function MarketingHeader() {
  const t = useTranslations('marketing');

  return (
    <header className="app-header">
      <div className="app-header__left">
        <p className="app-header__workspace">{t('title')}</p>
      </div>
      <div className="dashboard__header-actions app-header__actions">
        <AiGlobalButton />
        <ThemeToggle />
        <LanguageSelector />
        <NotificationBell />
        <WorkspaceHeaderUser />
      </div>
    </header>
  );
}
