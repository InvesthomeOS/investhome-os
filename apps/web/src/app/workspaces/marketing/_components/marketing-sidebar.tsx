'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canReadMarketing, filterNavByPermission } from '@/lib/marketing/marketing-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { MARKETING_NAV_GROUPS } from '@/workspaces/marketing/types';
import { useMarketingWorkspaceStore } from '@/workspaces/marketing/stores/marketing-workspace-store';

const MARKETING_NAV_ICONS: Record<string, IhIconName> = {
  'nav.dashboard': 'home',
  'nav.campaigns': 'target',
  'nav.assets': 'documents',
  'nav.reports': 'barChart',
  'nav.aiAssistant': 'sparkles',
  'nav.calendar': 'calendar',
  'nav.settings': 'settings',
  'nav.audiences': 'users',
  'nav.segments': 'crm',
  'nav.leads': 'sales',
  'nav.sources': 'trendingUp',
  'nav.landingPages': 'design',
  'nav.forms': 'documents',
  'nav.contentStudio': 'design',
  'nav.social': 'activity',
  'nav.email': 'inbox',
  'nav.whatsapp': 'inbox',
  'nav.sms': 'bell',
  'nav.templates': 'documents',
  'nav.advertising': 'trendingUp',
  'nav.budgets': 'finance',
  'nav.attribution': 'target',
  'nav.analytics': 'barChart',
  'nav.forecasting': 'sparkles',
  'nav.ai': 'sparkles',
  'nav.events': 'calendar',
  'nav.brand': 'design',
  'nav.automations': 'refresh',
  'nav.approvals': 'check',
  'nav.vendors': 'investors',
};

/** Marketing secondary rail — sits beside OS SidebarNav inside the unified shell. */
export function MarketingSidebar() {
  const pathname = usePathname();
  const t = useTranslations('marketing');
  const tNav = useTranslations('navigation');
  const { user, loading: authLoading } = useAuth();
  const sidebarCollapsed = useMarketingWorkspaceStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useMarketingWorkspaceStore((state) => state.toggleSidebar);

  const shellClass = sidebarCollapsed
    ? 'os-workspace-rail os-workspace-rail--collapsed marketing-shell__sidebar'
    : 'os-workspace-rail marketing-shell__sidebar';

  if (authLoading) {
    return <aside className={shellClass} aria-busy="true" />;
  }

  if (!canReadMarketing(user)) {
    return null;
  }

  const navGroups = filterNavByPermission(user, MARKETING_NAV_GROUPS);

  return (
    <aside className={shellClass}>
      <div className="os-workspace-rail__header">
        <p className="os-workspace-rail__title">{t('title')}</p>
        <button
          type="button"
          className="os-workspace-rail__toggle"
          onClick={toggleSidebar}
          aria-label={sidebarCollapsed ? t('expandSidebar') : t('collapseSidebar')}
        >
          <IhIcon name={sidebarCollapsed ? 'chevronRight' : 'chevronLeft'} size={16} />
        </button>
      </div>

      <nav className="os-workspace-rail__nav" aria-label={t('navAriaLabel')}>
        {navGroups.map((group) => (
          <div key={group.key}>
            <div className="os-workspace-rail__section">{t(group.labelKey as 'nav.groups.overview')}</div>
            {group.items.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== '/workspaces/marketing/dashboard' && pathname.startsWith(`${item.href}/`));
              const label = t(item.labelKey as 'nav.dashboard');
              const icon = MARKETING_NAV_ICONS[item.labelKey] ?? 'marketing';
              return (
                <Link
                  key={item.href}
                  href={item.href as Route}
                  className={
                    isActive
                      ? 'os-workspace-rail__link os-workspace-rail__link--active'
                      : 'os-workspace-rail__link'
                  }
                  aria-current={isActive ? 'page' : undefined}
                  title={sidebarCollapsed ? label : undefined}
                >
                  <span className="os-workspace-rail__link-icon">
                    <IhIcon name={icon} size={18} />
                  </span>
                  <span className="os-workspace-rail__link-label">{label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="os-workspace-rail__footer">
        <Link
          href="/dashboard"
          className="os-workspace-rail__link os-workspace-rail__link--main-menu"
          title={sidebarCollapsed ? tNav('mainMenu') : undefined}
          data-testid="os-main-menu"
        >
          <span className="os-workspace-rail__link-icon">
            <IhIcon name="home" size={18} />
          </span>
          <span className="os-workspace-rail__link-label">{tNav('mainMenu')}</span>
        </Link>
      </div>
    </aside>
  );
}
