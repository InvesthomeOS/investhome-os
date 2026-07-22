'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { BrandLogo } from '@/components/brand/brand-logo';

import { BiFilterBar } from './bi-filter-bar';

const TABS = [
  { href: '/dashboard/analytics', key: 'executive', exact: true },
  { href: '/dashboard/analytics/sales', key: 'sales' },
  { href: '/dashboard/analytics/marketing', key: 'marketing' },
  { href: '/dashboard/analytics/investors', key: 'investor' },
  { href: '/dashboard/analytics/finance', key: 'finance' },
  { href: '/dashboard/analytics/projects', key: 'project' },
  { href: '/dashboard/analytics/portfolio', key: 'portfolio' },
  { href: '/dashboard/analytics/website', key: 'website' },
  { href: '/dashboard/analytics/operational', key: 'operational' },
  { href: '/dashboard/analytics/reports', key: 'reports' },
  { href: '/dashboard/analytics/explorer', key: 'explorer' },
  { href: '/dashboard/analytics/data-quality', key: 'dataQuality' },
] as const;

export function BiWorkspaceShell({
  title,
  subtitle,
  children,
  actions,
  showFilters = true,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
  showFilters?: boolean;
}) {
  const pathname = usePathname();
  const t = useTranslations('analytics');
  const tNav = useTranslations('analytics.nav');

  return (
    <main className="dashboard bi-workspace" data-bi-workspace>
      <header className="bi-workspace__header">
        <div>
          <p className="bi-workspace__eyebrow">{t('eyebrow')}</p>
          <h1 className="bi-workspace__title">{title}</h1>
          {subtitle ? <p className="bi-workspace__subtitle">{subtitle}</p> : null}
        </div>
        <div className="bi-workspace__header-actions">
          {actions}
          <BrandLogo layout="mark" />
        </div>
      </header>

      <nav className="bi-workspace__nav" aria-label={tNav('aria')}>
        {TABS.map((tab) => {
          const active = tab.exact
            ? pathname === tab.href
            : pathname === tab.href || pathname.startsWith(`${tab.href}/`);
          return (
            <Link
              key={tab.key}
              href={tab.href as Route}
              className={`bi-workspace__nav-link${active ? ' bi-workspace__nav-link--active' : ''}`}
              aria-current={active ? 'page' : undefined}
            >
              {tNav(tab.key)}
            </Link>
          );
        })}
      </nav>

      {showFilters ? <BiFilterBar /> : null}
      {children}
    </main>
  );
}
