'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

const MODULE_KEYS: Record<string, string> = {
  executive: 'executive',
  leads: 'leads',
  investors: 'investors',
  projects: 'projects',
  inventory: 'inventory',
  finance: 'finance',
  documents: 'documents',
  design: 'designStudio',
  activity: 'activity',
  settings: 'settings',
  profile: 'profile',
  admin: 'adminSection',
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tCommon = useTranslations('common');
  const tProfile = useTranslations('profile');

  const segments = pathname.split('/').filter(Boolean);

  if (segments.length <= 1) {
    return null;
  }

  const crumbs: { href: Route; label: string }[] = [
    { href: '/dashboard' as Route, label: tCommon('appName') },
  ];

  if (segments[1] === 'admin' && segments[2]) {
    crumbs.push({ href: '/dashboard/admin/users' as Route, label: t('adminSection') });
    const adminKey = segments[2];
    if (adminKey === 'users') {
      crumbs.push({ href: pathname as Route, label: t('admin.users') });
    } else if (adminKey === 'roles') {
      crumbs.push({ href: pathname as Route, label: t('admin.roles') });
    } else if (adminKey === 'permissions') {
      crumbs.push({ href: pathname as Route, label: t('admin.permissions') });
    }
  } else if (segments[1]) {
    const moduleKey = segments[1];
    const navKey = MODULE_KEYS[moduleKey];
    let label = navKey ? t(navKey as 'documents') : moduleKey;

    if (moduleKey === 'profile') {
      label = tProfile('title');
    } else if (navKey?.startsWith('modules.')) {
      label = t(`modules.${moduleKey}.title` as 'modules.executive.title');
    } else if (MODULE_KEYS[moduleKey]?.startsWith('modules') || ['executive', 'leads', 'investors', 'projects', 'inventory', 'finance'].includes(moduleKey)) {
      label = t(`modules.${moduleKey}.title` as 'modules.executive.title');
    }

    crumbs.push({
      href: (`/dashboard/${moduleKey}`) as Route,
      label,
    });

    if (segments[2] && moduleKey === 'design') {
      const sub = segments[2];
      if (sub === 'furniture') {
        crumbs.push({ href: pathname as Route, label: t('designStudio') });
      }
    }
  }

  if (crumbs.length <= 1) {
    return null;
  }

  return (
    <nav className="app-breadcrumbs" aria-label={t('breadcrumbs')}>
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
