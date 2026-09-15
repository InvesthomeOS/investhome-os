'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canReadCrm } from '@/lib/crm/crm-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { CRM_NAV_ITEMS } from '@/workspaces/crm/types';
import { useCrmWorkspaceStore } from '@/workspaces/crm/_stores/crm-workspace-store';

const CRM_NAV_ICONS: Record<string, IhIconName> = {
  'nav.dashboard': 'home',
  'nav.leads': 'target',
  'nav.pipeline': 'barChart',
  'nav.matches': 'inventory',
  'nav.contacts': 'users',
  'nav.junk': 'inbox',
  'nav.agents': 'user',
  'nav.agreements': 'documents',
  'nav.companies': 'investors',
  'nav.investors': 'trendingUp',
  'nav.relationships': 'crm',
  'nav.timeline': 'activity',
  'nav.activities': 'calendar',
  'nav.tasks': 'check',
  'nav.calendar': 'calendar',
  'nav.notes': 'documents',
  'nav.tags': 'target',
  'nav.communication': 'inbox',
  'nav.documents': 'documents',
  'nav.reports': 'barChart',
  'nav.settings': 'settings',
};

/** Presentation-only management rail items (Admin foundation / UX review). */
const ADMIN_NAV_ITEMS: ReadonlyArray<{
  href: string;
  labelKey: 'nav.admin' | 'nav.systemLogs' | 'nav.integrations';
  icon: IhIconName;
  badgeKey?: 'nav.adminBadge';
}> = [
  { href: '/dashboard/admin', labelKey: 'nav.admin', icon: 'admin', badgeKey: 'nav.adminBadge' },
  { href: '/dashboard/admin/audit', labelKey: 'nav.systemLogs', icon: 'activity' },
  { href: '/dashboard/admin/platform/integrations', labelKey: 'nav.integrations', icon: 'settings' },
];

function isAdminWorkspacePath(pathname: string) {
  return (
    pathname === '/dashboard/admin' ||
    pathname.startsWith('/dashboard/admin/') ||
    pathname === '/workspaces/admin' ||
    pathname.startsWith('/workspaces/admin/') ||
    pathname.startsWith('/ui-preview/crm/admin') ||
    pathname.startsWith('/ui-preview/admin')
  );
}

function isAdminNavActive(pathname: string, href: string) {
  if (href === '/dashboard/admin') {
    return (
      pathname === '/dashboard/admin' ||
      pathname === '/dashboard/admin/' ||
      pathname === '/workspaces/admin' ||
      pathname === '/workspaces/admin/'
    );
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** CRM secondary rail — sits beside OS SidebarNav inside the unified shell. */
export function CrmSidebar() {
  const pathname = usePathname();
  const t = useTranslations('crm');
  const tNav = useTranslations('navigation');
  const { user, loading: authLoading } = useAuth();
  const sidebarCollapsed = useCrmWorkspaceStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useCrmWorkspaceStore((state) => state.toggleSidebar);

  const shellClass = sidebarCollapsed
    ? 'os-workspace-rail os-workspace-rail--collapsed crm-shell__sidebar'
    : 'os-workspace-rail crm-shell__sidebar';

  if (authLoading) {
    return <aside className={shellClass} aria-busy="true" />;
  }

  if (!canReadCrm(user)) {
    return null;
  }

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
        <div className="os-workspace-rail__section">{t('nav.section')}</div>
        {CRM_NAV_ITEMS.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== '/workspaces/crm/dashboard' && pathname.startsWith(`${item.href}/`)) ||
            (item.href === '/workspaces/crm/pipeline' &&
              pathname.startsWith('/ui-preview/crm/opportunities')) ||
            (item.href === '/workspaces/crm/matches' &&
              pathname.startsWith('/ui-preview/crm/matches')) ||
            (item.href === '/workspaces/crm/documents' &&
              pathname.startsWith('/ui-preview/crm/documents')) ||
            (item.href === '/workspaces/crm/activities' &&
              pathname.startsWith('/ui-preview/crm/activities')) ||
            (item.href === '/workspaces/crm/tasks' &&
              pathname.startsWith('/ui-preview/crm/tasks')) ||
            (item.href === '/workspaces/crm/calendar' &&
              pathname.startsWith('/ui-preview/crm/calendar')) ||
            (item.href === '/workspaces/crm/companies' &&
              pathname.startsWith('/ui-preview/crm/companies')) ||
            (item.href === '/workspaces/crm/investors' &&
              (pathname.startsWith('/ui-preview/crm/investors') ||
                pathname.startsWith('/workspaces/crm/investors'))) ||
            (item.href === '/workspaces/crm/reports' &&
              pathname.startsWith('/ui-preview/crm/reports')) ||
            (item.href === '/workspaces/crm/settings' &&
              pathname.startsWith('/ui-preview/crm/settings')) ||
            (item.href === '/workspaces/crm/contacts' &&
              (pathname.startsWith('/ui-preview/crm/people') ||
                pathname.startsWith('/workspaces/crm/people')));
          const label = t(item.labelKey as 'nav.dashboard');
          const icon = CRM_NAV_ICONS[item.labelKey] ?? 'crm';
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

        {isAdminWorkspacePath(pathname) ? (
          <>
            <div className="os-workspace-rail__section">{t('nav.adminSection')}</div>
            {ADMIN_NAV_ITEMS.map((item) => {
              const isActive = isAdminNavActive(pathname, item.href);
              const label = t(item.labelKey);
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
                    <IhIcon name={item.icon} size={18} />
                  </span>
                  <span className="os-workspace-rail__link-label">{label}</span>
                  {item.badgeKey && !sidebarCollapsed ? (
                    <span className="os-workspace-rail__link-badge">{t(item.badgeKey)}</span>
                  ) : null}
                </Link>
              );
            })}
          </>
        ) : null}
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
