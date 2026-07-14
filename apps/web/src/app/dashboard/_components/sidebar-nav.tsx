'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

function moduleHref(module: ModuleName): Route {
  return `/dashboard/${module}` as Route;
}

export function SidebarNav() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tCommon = useTranslations('common');

  return (
    <aside className="dashboard-shell__sidebar">
      <div className="dashboard-shell__brand">
        <Link href="/dashboard" className="dashboard-shell__brand-link">
          <span className="dashboard__eyebrow">{tCommon('appName')}</span>
          <span className="dashboard-shell__brand-title">{tCommon('operations')}</span>
        </Link>
      </div>

      <nav className="dashboard-shell__nav" aria-label={t('ariaLabel')}>
        {MODULE_NAMES.map((module) => {
          const href = moduleHref(module);
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          const isImplemented = module === 'leads' || module === 'investors';

          return (
            <Link
              key={module}
              href={href}
              className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
            >
              <span>{t(`modules.${module}.title`)}</span>
              {!isImplemented && (
                <span className="dashboard-shell__nav-badge">{tCommon('soon')}</span>
              )}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
