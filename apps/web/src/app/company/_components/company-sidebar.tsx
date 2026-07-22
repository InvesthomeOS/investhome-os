'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canReadBranch } from '@/lib/company/branch-permissions';
import { canReadCompany } from '@/lib/company/company-permissions';
import { useCompanyWorkspaceStore } from '@/lib/company/company-workspace-store';
import { useAuth } from '@/lib/auth/auth-context';

type NavItem = {
  href: string;
  labelKey: string;
  permission?: 'read' | 'branch.read';
  icon: IhIconName;
};

const NAV_ITEMS: NavItem[] = [
  { href: '/company', labelKey: 'nav.overview', icon: 'home' },
  { href: '/company/companies', labelKey: 'nav.companies', permission: 'read', icon: 'investors' },
  { href: '/company/organization', labelKey: 'nav.organization', permission: 'read', icon: 'executive' },
  { href: '/company/branches', labelKey: 'nav.branches', permission: 'branch.read', icon: 'projects' },
  { href: '/company/departments', labelKey: 'nav.departments', permission: 'read', icon: 'roles' },
  { href: '/company/teams', labelKey: 'nav.teams', permission: 'read', icon: 'users' },
  { href: '/company/employees', labelKey: 'nav.employees', permission: 'read', icon: 'user' },
  { href: '/company/documents', labelKey: 'nav.documents', permission: 'read', icon: 'documents' },
  { href: '/company/assets', labelKey: 'nav.assets', permission: 'read', icon: 'inventory' },
  { href: '/company/settings', labelKey: 'nav.settings', permission: 'read', icon: 'settings' },
];

/** Company secondary rail — sits beside OS SidebarNav inside the unified shell. */
export function CompanySidebar() {
  const pathname = usePathname();
  const t = useTranslations('company');
  const tNav = useTranslations('navigation');
  const { user } = useAuth();
  const sidebarCollapsed = useCompanyWorkspaceStore((state) => state.sidebarCollapsed);
  const toggleSidebar = useCompanyWorkspaceStore((state) => state.toggleSidebar);

  const shellClass = sidebarCollapsed
    ? 'os-workspace-rail os-workspace-rail--collapsed company-shell__sidebar'
    : 'os-workspace-rail company-shell__sidebar';

  return (
    <aside className={shellClass}>
      <div className="os-workspace-rail__header">
        <p className="os-workspace-rail__title">{t('nav.section')}</p>
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
        {NAV_ITEMS.map((item) => {
          if (item.permission === 'read' && !canReadCompany(user)) {
            return null;
          }
          if (item.permission === 'branch.read' && !canReadBranch(user)) {
            return null;
          }
          const isActive =
            item.href === '/company'
              ? pathname === '/company' || pathname === '/company/overview'
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const label = t(item.labelKey as 'nav.overview');
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
            </Link>
          );
        })}
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
