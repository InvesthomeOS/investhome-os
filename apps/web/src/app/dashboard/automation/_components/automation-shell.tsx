'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

const TABS = [
  { href: '/dashboard/automation', key: 'overview', exact: true },
  { href: '/dashboard/automation/workflows', key: 'workflows' },
  { href: '/dashboard/automation/executions', key: 'executions' },
  { href: '/dashboard/automation/errors', key: 'errors' },
  { href: '/dashboard/automation/schedules', key: 'schedules' },
  { href: '/dashboard/automation/integrations', key: 'integrations' },
  { href: '/dashboard/automation/audit', key: 'audit' },
] as const;

export function AutomationShell({
  title,
  subtitle,
  children,
  actions,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}) {
  const pathname = usePathname();
  const t = useTranslations('automation');
  const tNav = useTranslations('automation.nav');

  return (
    <main className="dashboard automation-center" data-automation-center>
      <header className="automation-center__header">
        <div>
          <p className="automation-center__eyebrow">{t('eyebrow')}</p>
          <h1 className="automation-center__title">{title}</h1>
          {subtitle ? <p className="automation-center__subtitle">{subtitle}</p> : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </header>

      <nav className="automation-center__nav" aria-label={tNav('aria')}>
        {TABS.map((tab) => {
          const active = tab.exact
            ? pathname === tab.href
            : pathname === tab.href || pathname.startsWith(`${tab.href}/`);
          return (
            <Link
              key={tab.key}
              href={tab.href as Route}
              className={`automation-center__nav-link${active ? ' automation-center__nav-link--active' : ''}`}
              aria-current={active ? 'page' : undefined}
            >
              {tNav(tab.key)}
            </Link>
          );
        })}
      </nav>

      {children}
    </main>
  );
}
