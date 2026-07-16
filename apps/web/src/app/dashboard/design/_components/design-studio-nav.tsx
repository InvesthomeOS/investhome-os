'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';

const NAV_ITEMS = [
  { href: '/dashboard/design', key: 'projects' as const, exact: true },
  { href: '/dashboard/design/style-presets', key: 'stylePresets' as const, exact: false },
  { href: '/dashboard/design/material-packages', key: 'materialPackages' as const, exact: false },
  { href: '/dashboard/design/furniture', key: 'furnitureLibrary' as const, exact: false },
];

export function DesignStudioNav() {
  const pathname = usePathname();
  const t = useTranslations('design.nav');

  return (
    <nav className="documents-tabs design-studio-nav" aria-label={t('ariaLabel')}>
      {NAV_ITEMS.map((item) => {
        const isActive = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href as Route}
            className={`documents-tabs__tab${isActive ? ' documents-tabs__tab--active' : ''}`}
            aria-current={isActive ? 'page' : undefined}
          >
            {t(item.key)}
          </Link>
        );
      })}
    </nav>
  );
}
