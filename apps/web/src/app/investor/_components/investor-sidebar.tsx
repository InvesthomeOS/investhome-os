'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { WorkspaceSidebarBrand } from '@/components/shell/workspace-sidebar-brand';

import { investorProfile } from '../_data/mock-data';
import type { InvestorNavItem } from '../_data/types';
import { useMessagingStateOptional } from '../_state/messaging-state';
import { useDocumentsState } from '../_state/documents-state';

const NAV_ITEMS: InvestorNavItem[] = [
  { href: '/investor', label: 'Dashboard', matchPaths: ['/investor', '/investor/dashboard'] },
  { href: '/investor/investments', label: 'My Investments' },
  { href: '/investor/portfolio', label: 'Portfolio' },
  { href: '/investor/distributions', label: 'Distributions' },
  { href: '/investor/performance', label: 'Performance' },
  { href: '/investor/documents', label: 'Documents' },
  { href: '/investor/messages', label: 'Messages' },
  { href: '/investor/tasks', label: 'Tasks' },
  { href: '/investor/profile', label: 'Profile' },
  { href: '/investor/settings', label: 'Settings' },
];

const NAV_ICONS: Record<string, IhIconName> = {
  Dashboard: 'home',
  'My Investments': 'investors',
  Portfolio: 'barChart',
  Distributions: 'finance',
  Performance: 'trendingUp',
  Documents: 'documents',
  Messages: 'inbox',
  Tasks: 'check',
  Profile: 'user',
  Settings: 'settings',
};

function isNavActive(pathname: string, item: InvestorNavItem): boolean {
  if (item.matchPaths) {
    return item.matchPaths.includes(pathname);
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

interface InvestorSidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

function NavBadge({ count }: { count: number }) {
  if (count <= 0) return null;
  return (
    <span className="dashboard-shell__nav-badge investor-sidebar__badge" aria-label={`${count} items need attention`}>
      {count > 99 ? '99+' : count}
    </span>
  );
}

const BADGE_NAV_LABELS = new Set(['Messages', 'Tasks']);

export function InvestorSidebar({ collapsed, onToggleCollapsed }: InvestorSidebarProps) {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const messagingState = useMessagingStateOptional();
  const unreadMessages = messagingState?.sidebarBadges.unreadMessages ?? 0;
  const openTasks = messagingState?.sidebarBadges.openTasks ?? 0;
  const { sidebarBadges } = useDocumentsState();

  function getNavBadge(label: string): number | null {
    if (label === 'Messages' && unreadMessages > 0) return unreadMessages;
    if (label === 'Tasks' && openTasks > 0) return openTasks;
    return null;
  }

  const shellClass = collapsed
    ? 'dashboard-shell__sidebar dashboard-shell__sidebar--collapsed investor-shell__sidebar'
    : 'dashboard-shell__sidebar investor-shell__sidebar';

  return (
    <aside className={shellClass}>
      <WorkspaceSidebarBrand
        href="/investor"
        collapsed={collapsed}
        ariaLabel={t('modules.investors.title')}
        workspaceChip={t('modules.investors.title')}
        onToggleCollapsed={onToggleCollapsed}
        expandLabel={t('expandSidebar')}
        collapseLabel={t('collapseSidebar')}
      />

      <nav className="dashboard-shell__nav" aria-label="Investor navigation">
        <div className="dashboard-shell__nav-section">Portfolio</div>
        {NAV_ITEMS.slice(0, 5).map((item) => {
          const active = isNavActive(pathname, item);
          return (
            <Link
              key={item.href}
              href={item.href as Route}
              className={`dashboard-shell__nav-link${active ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={active ? 'page' : undefined}
              title={collapsed ? item.label : undefined}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={NAV_ICONS[item.label] ?? 'investors'} size={18} />
              </span>
              <span className="dashboard-shell__nav-link-label">{item.label}</span>
              {item.label === 'Documents' ? <NavBadge count={sidebarBadges.total} /> : null}
            </Link>
          );
        })}

        <div className="dashboard-shell__nav-section">Account</div>
        {NAV_ITEMS.slice(5).map((item) => {
          const active = isNavActive(pathname, item);
          const badge = BADGE_NAV_LABELS.has(item.label) ? getNavBadge(item.label) : null;
          return (
            <Link
              key={item.href}
              href={item.href as Route}
              className={`dashboard-shell__nav-link${active ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={active ? 'page' : undefined}
              title={collapsed ? item.label : undefined}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={NAV_ICONS[item.label] ?? 'user'} size={18} />
              </span>
              <span className="dashboard-shell__nav-link-label">{item.label}</span>
              {badge !== null ? (
                <span className="dashboard-shell__nav-badge" aria-label={`${badge} pending`}>
                  {badge > 99 ? '99+' : badge}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className="dashboard-shell__sidebar-footer investor-shell__sidebar-footer">
        <span className="investor-sidebar__tier-badge">{investorProfile.investorTier} Investor</span>
      </div>
    </aside>
  );
}
