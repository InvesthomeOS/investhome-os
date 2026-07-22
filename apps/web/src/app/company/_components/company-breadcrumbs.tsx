'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

const SEGMENT_KEYS: Record<string, string> = {
  company: 'nav.overview',
  overview: 'nav.overview',
  companies: 'nav.companies',
  organization: 'nav.organization',
  branches: 'nav.branches',
  departments: 'nav.departments',
  teams: 'nav.teams',
  employees: 'nav.employees',
  documents: 'nav.documents',
  assets: 'nav.assets',
  settings: 'nav.settings',
};

export function CompanyBreadcrumbs() {
  const pathname = usePathname();
  const t = useTranslations('company');
  const tCommon = useTranslations('common');

  const segments = pathname.split('/').filter(Boolean);
  if (segments.length <= 1) {
    return null;
  }

  const crumbs: { href: Route; label: string }[] = [
    { href: '/company' as Route, label: t('title') },
  ];

  const section = segments[1];
  if (section && section !== 'overview') {
    const key = SEGMENT_KEYS[section];
    crumbs.push({
      href: pathname as Route,
      label: key ? t(key as 'nav.overview') : section,
    });
  } else if (section === 'overview') {
    crumbs.push({ href: '/company/overview' as Route, label: t('nav.overview') });
  }

  if (crumbs.length <= 1) {
    return null;
  }

  return (
    <nav className="app-breadcrumbs" aria-label={tCommon('appName')}>
      <ol className="app-breadcrumbs__list">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <li key={crumb.href} className="app-breadcrumbs__item">
              {isLast ? (
                <span className="app-breadcrumbs__current" aria-current="page">
                  {crumb.label}
                </span>
              ) : (
                <Link href={crumb.href} className="app-breadcrumbs__link">
                  {crumb.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
