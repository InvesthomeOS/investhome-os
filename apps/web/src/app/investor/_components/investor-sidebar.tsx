'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { WorkspaceSidebarBrand } from '@/components/shell/workspace-sidebar-brand';

import { investorProfile } from '../_data/mock-data';
import { useMessagingStateOptional } from '../_state/messaging-state';
import { useDocumentsState } from '../_state/documents-state';

type NavId =
  | 'dashboard'
  | 'investments'
  | 'portfolio'
  | 'distributions'
  | 'performance'
  | 'documents'
  | 'messages'
  | 'tasks'
  | 'profile'
  | 'settings';

const NAV_ITEMS: Array<{
  id: NavId;
  href: string;
  matchPaths?: string[];
}> = [
  { id: 'dashboard', href: '/investor', matchPaths: ['/investor', '/investor/dashboard'] },
  { id: 'investments', href: '/investor/investments' },
  { id: 'portfolio', href: '/investor/portfolio' },
  { id: 'distributions', href: '/investor/distributions' },
  { id: 'performance', href: '/investor/performance' },
  { id: 'documents', href: '/investor/documents' },
  { id: 'messages', href: '/investor/messages' },
  { id: 'tasks', href: '/investor/tasks' },
  { id: 'profile', href: '/investor/profile' },
  { id: 'settings', href: '/investor/settings' },
];

const NAV_ICONS: Record<NavId, IhIconName> = {
  dashboard: 'home',
  investments: 'investors',
  portfolio: 'barChart',
  distributions: 'finance',
  performance: 'trendingUp',
  documents: 'documents',
  messages: 'inbox',
  tasks: 'check',
  profile: 'user',
  settings: 'settings',
};

function isNavActive(pathname: string, item: (typeof NAV_ITEMS)[number]): boolean {
  if (item.matchPaths) {
    return item.matchPaths.includes(pathname);
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

interface InvestorSidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

function NavBadge({ count, label }: { count: number; label: string }) {
  if (count <= 0) return null;
  return (
    <span className="dashboard-shell__nav-badge investor-sidebar__badge" aria-label={label}>
      {count > 99 ? '99+' : count}
    </span>
  );
}

export function InvestorSidebar({ collapsed, onToggleCollapsed }: InvestorSidebarProps) {
  const pathname = usePathname();
  const tNav = useTranslations('navigation');
  const t = useTranslations('investorPortal');
  const messagingState = useMessagingStateOptional();
  const unreadMessages = messagingState?.sidebarBadges.unreadMessages ?? 0;
  const openTasks = messagingState?.sidebarBadges.openTasks ?? 0;
  const { sidebarBadges } = useDocumentsState();

  function getNavBadge(id: NavId): number | null {
    if (id === 'messages' && unreadMessages > 0) return unreadMessages;
    if (id === 'tasks' && openTasks > 0) return openTasks;
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
        ariaLabel={tNav('modules.investors.title')}
        workspaceChip={tNav('modules.investors.title')}
        onToggleCollapsed={onToggleCollapsed}
        expandLabel={tNav('expandSidebar')}
        collapseLabel={tNav('collapseSidebar')}
      />

      <nav className="dashboard-shell__nav" aria-label={t('navAriaLabel')}>
        <div className="dashboard-shell__nav-section">{t('sections.portfolio')}</div>
        {NAV_ITEMS.slice(0, 5).map((item) => {
          const active = isNavActive(pathname, item);
          const label = t(`nav.${item.id}`);
          return (
            <Link
              key={item.href}
              href={item.href as Route}
              className={`dashboard-shell__nav-link${active ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={active ? 'page' : undefined}
              title={collapsed ? label : undefined}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={NAV_ICONS[item.id]} size={18} />
              </span>
              <span className="dashboard-shell__nav-link-label">{label}</span>
              {item.id === 'documents' ? (
                <NavBadge count={sidebarBadges.total} label={t('badgeAttention', { count: sidebarBadges.total })} />
              ) : null}
            </Link>
          );
        })}

        <div className="dashboard-shell__nav-section">{t('sections.account')}</div>
        {NAV_ITEMS.slice(5).map((item) => {
          const active = isNavActive(pathname, item);
          const label = t(`nav.${item.id}`);
          const badge = item.id === 'messages' || item.id === 'tasks' ? getNavBadge(item.id) : null;
          return (
            <Link
              key={item.href}
              href={item.href as Route}
              className={`dashboard-shell__nav-link${active ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={active ? 'page' : undefined}
              title={collapsed ? label : undefined}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={NAV_ICONS[item.id]} size={18} />
              </span>
              <span className="dashboard-shell__nav-link-label">{label}</span>
              {badge !== null ? (
                <span className="dashboard-shell__nav-badge" aria-label={t('badgePending', { count: badge })}>
                  {badge > 99 ? '99+' : badge}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className="dashboard-shell__sidebar-footer investor-shell__sidebar-footer">
        <span className="investor-sidebar__tier-badge">
          {t('tierBadge', {
            tier: t(`tiers.${investorProfile.investorTier}` as 'tiers.platinum'),
          })}
        </span>
      </div>
    </aside>
  );
}
