'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { WorkspaceSidebarBrand } from '@/components/shell/workspace-sidebar-brand';

import { usePortalSession } from '../_state/portal-session';

type NavItem = {
  href: Route;
  labelKey: string;
  icon: IhIconName;
  match?: string[];
};

const PORTFOLIO_NAV: NavItem[] = [
  { href: '/portal' as Route, labelKey: 'nav.dashboard', icon: 'home', match: ['/portal', '/portal/dashboard'] },
  { href: '/portal/portfolio' as Route, labelKey: 'nav.portfolio', icon: 'barChart' },
  { href: '/portal/projects' as Route, labelKey: 'nav.projects', icon: 'projects' },
  { href: '/portal/reservations' as Route, labelKey: 'nav.reservations', icon: 'calendar' },
  { href: '/portal/contracts' as Route, labelKey: 'nav.contracts', icon: 'documents' },
  { href: '/portal/payments' as Route, labelKey: 'nav.payments', icon: 'finance' },
  { href: '/portal/rental-income' as Route, labelKey: 'nav.rental', icon: 'trendingUp' },
];

const OPS_NAV: NavItem[] = [
  { href: '/portal/documents' as Route, labelKey: 'nav.documents', icon: 'documents' },
  { href: '/portal/reports' as Route, labelKey: 'nav.reports', icon: 'barChart' },
  { href: '/portal/messages' as Route, labelKey: 'nav.messages', icon: 'inbox' },
  { href: '/portal/tasks' as Route, labelKey: 'nav.tasks', icon: 'check' },
  { href: '/portal/meetings' as Route, labelKey: 'nav.meetings', icon: 'meeting' },
  { href: '/portal/notifications' as Route, labelKey: 'nav.notifications', icon: 'bell' },
];

const ACCOUNT_NAV: NavItem[] = [
  { href: '/portal/help' as Route, labelKey: 'nav.help', icon: 'inbox' },
  { href: '/portal/support' as Route, labelKey: 'nav.support', icon: 'inbox' },
  { href: '/portal/account' as Route, labelKey: 'nav.account', icon: 'settings' },
];
function isActive(pathname: string, item: NavItem): boolean {
  if (item.match) return item.match.includes(pathname);
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavSection({
  title,
  items,
  collapsed,
}: {
  title: string;
  items: NavItem[];
  collapsed: boolean;
}) {
  const pathname = usePathname();
  const t = useTranslations('portalG9');
  return (
    <>
      <div className="dashboard-shell__nav-section">{title}</div>
      {items.map((item) => {
        const active = isActive(pathname, item);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`dashboard-shell__nav-link${active ? ' dashboard-shell__nav-link--active' : ''}`}
            aria-current={active ? 'page' : undefined}
            title={collapsed ? t(item.labelKey) : undefined}
            data-testid={`portal-nav-${item.labelKey.split('.').pop()}`}
          >
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name={item.icon} size={18} />
            </span>
            <span className="dashboard-shell__nav-link-label">{t(item.labelKey)}</span>
          </Link>
        );
      })}
    </>
  );
}

export function PortalSidebar({
  collapsed,
  onToggleCollapsed,
}: {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  const t = useTranslations('portalG9');
  const tNav = useTranslations('navigation');
  const { profile } = usePortalSession();
  const shellClass = collapsed
    ? 'dashboard-shell__sidebar dashboard-shell__sidebar--collapsed portal-shell__sidebar'
    : 'dashboard-shell__sidebar portal-shell__sidebar';

  return (
    <aside className={shellClass} data-testid="portal-sidebar">
      <WorkspaceSidebarBrand
        href={"/portal" as Route}
        collapsed={collapsed}
        ariaLabel={t('portal')}
        workspaceChip={t('portal')}
        onToggleCollapsed={onToggleCollapsed}
        expandLabel={tNav('expandSidebar')}
        collapseLabel={tNav('collapseSidebar')}
      />
      <nav className="dashboard-shell__nav" aria-label={t('portal')}>
        <NavSection title={t('nav.sectionPortfolio')} items={PORTFOLIO_NAV} collapsed={collapsed} />
        <NavSection title={t('nav.sectionOps')} items={OPS_NAV} collapsed={collapsed} />
        <NavSection title={t('nav.sectionAccount')} items={ACCOUNT_NAV} collapsed={collapsed} />
      </nav>
      <div className="dashboard-shell__sidebar-footer">
        <span className="portal-shell__tier">
          {profile?.tier ?? 'investor'} · {profile?.avatarInitials ?? '—'}
        </span>
      </div>
    </aside>
  );
}
