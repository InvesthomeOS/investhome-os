'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

const DASHBOARD_TABS = [
  { href: '/workspaces/marketing/dashboard', key: 'hub' },
  { href: '/workspaces/marketing/dashboard/executive', key: 'executive' },
  { href: '/workspaces/marketing/dashboard/performance', key: 'performance' },
  { href: '/workspaces/marketing/dashboard/funnel', key: 'funnel' },
  { href: '/workspaces/marketing/dashboard/channels', key: 'channels' },
  { href: '/workspaces/marketing/dashboard/projects', key: 'projects' },
  { href: '/workspaces/marketing/dashboard/audiences', key: 'audiences' },
  { href: '/workspaces/marketing/dashboard/tracking', key: 'tracking' },
  { href: '/workspaces/marketing/dashboard/health', key: 'health' },
  { href: '/workspaces/marketing/dashboard/widgets', key: 'widgets' },
  { href: '/workspaces/marketing/dashboard/settings', key: 'settings' },
] as const;

export function DashboardSubNav() {
  const pathname = usePathname();
  const t = useTranslations('marketing.analytics.tabs');

  return (
    <nav className="mkt-dashboard-nav" aria-label={t('ariaLabel')}>
      {DASHBOARD_TABS.map((tab) => {
        const isActive = pathname === tab.href || (tab.key !== 'hub' && pathname.startsWith(tab.href));
        return (
          <Link
            key={tab.key}
            href={tab.href as Route}
            className={isActive ? 'mkt-dashboard-nav__link mkt-dashboard-nav__link--active' : 'mkt-dashboard-nav__link'}
          >
            {t(tab.key)}
          </Link>
        );
      })}
    </nav>
  );
}

export function DashboardPageShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  const tHub = useTranslations('marketing.analytics.hub');

  return (
    <main className="dashboard marketing-dashboard mkt-analytics-dashboard">
      <header className="dashboard__header mkt-analytics-dashboard__header">
        <p className="dashboard__eyebrow mkt-analytics-dashboard__eyebrow">{tHub('title')}</p>
        <h1 className="dashboard__title">{title}</h1>
        {subtitle ? <p className="dashboard__subtitle">{subtitle}</p> : null}
      </header>
      <DashboardSubNav />
      {children}
    </main>
  );
}
