'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

import { BrandLogo } from '@/components/brand/brand-logo';

const TABS: ReadonlyArray<{ href: Route; key: string; exact?: boolean }> = [
  { href: '/dashboard/ai', key: 'home', exact: true },
  { href: '/dashboard/ai/prompts', key: 'prompts' },
  { href: '/dashboard/ai/history', key: 'history' },
  { href: '/dashboard/ai/settings', key: 'settings' },
];

export function AiWorkspaceShell({
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
  const t = useTranslations('ai');
  const tNav = useTranslations('ai.nav');

  return (
    <main className="dashboard ai-workspace" data-ai-workspace>
      <header className="ai-workspace__header">
        <div>
          <p className="ai-workspace__eyebrow">{t('eyebrow')}</p>
          <h1 className="ai-workspace__title">{title}</h1>
          {subtitle ? <p className="ai-workspace__subtitle">{subtitle}</p> : null}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {actions}
          <BrandLogo layout="mark" />
        </div>
      </header>

      <nav className="ai-workspace__nav" aria-label={tNav('aria')}>
        {TABS.map((tab) => {
          const active = tab.exact
            ? pathname === tab.href
            : pathname === tab.href || pathname.startsWith(`${tab.href}/`);
          return (
            <Link
              key={tab.key}
              href={tab.href}
              className={`ai-workspace__nav-link${active ? ' ai-workspace__nav-link--active' : ''}`}
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
