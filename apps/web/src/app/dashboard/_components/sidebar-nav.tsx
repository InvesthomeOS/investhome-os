'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useCompanyBranding } from '@/lib/company/company-context';
import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

function moduleHref(module: ModuleName): Route {
  return `/dashboard/${module}` as Route;
}

const MODULE_PERMISSIONS: Record<ModuleName, { resource: string; action: string }> = {
  executive: { resource: 'executive', action: 'view' },
  leads: { resource: 'leads', action: 'view' },
  investors: { resource: 'investors', action: 'view' },
  projects: { resource: 'projects', action: 'view' },
  finance: { resource: 'finance', action: 'view' },
};

export function SidebarNav() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tCommon = useTranslations('common');
  const { user, canViewAdmin } = useAuth();
  const { displayName, slogan } = useCompanyBranding();
  const canViewActivity = user ? hasPermission(user, 'activity', 'view') : false;
  const canViewDocuments = user ? hasPermission(user, 'documents', 'view') : false;
  const canViewDesign = user ? hasPermission(user, 'design', 'view') : false;
  const canViewSettings = user ? hasPermission(user, 'settings', 'view') || hasPermission(user, 'company', 'view') : false;

  return (
    <aside className="dashboard-shell__sidebar">
      <div className="dashboard-shell__brand">
        <Link href="/dashboard" className="dashboard-shell__brand-link">
          <span className="dashboard__eyebrow">{displayName}</span>
          <span className="dashboard-shell__brand-title">{slogan ?? tCommon('operations')}</span>
        </Link>
      </div>

      <nav className="dashboard-shell__nav" aria-label={t('ariaLabel')}>
        {MODULE_NAMES.map((module) => {
          const permission = MODULE_PERMISSIONS[module];
          const allowed = user ? hasPermission(user, permission.resource, permission.action) : false;
          if (!allowed) {
            return null;
          }

          const href = moduleHref(module);
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          const isImplemented =
            module === 'executive' ||
            module === 'leads' ||
            module === 'investors' ||
            module === 'projects' ||
            module === 'finance';

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

        {canViewDocuments && (
          <Link
            href={'/dashboard/documents' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/documents' || pathname.startsWith('/dashboard/documents/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/documents') ? 'page' : undefined}
          >
            <span>{t('documents')}</span>
          </Link>
        )}

        {canViewDesign && (
          <Link
            href={'/dashboard/design' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/design' || pathname.startsWith('/dashboard/design/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/design') ? 'page' : undefined}
          >
            <span>{t('designStudio')}</span>
          </Link>
        )}

        {canViewActivity && (
          <Link
            href={'/dashboard/activity' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/activity' || pathname.startsWith('/dashboard/activity/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/activity') ? 'page' : undefined}
          >
            <span>{t('activity')}</span>
          </Link>
        )}

        {canViewSettings && (
          <Link
            href={'/dashboard/settings' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/settings' || pathname.startsWith('/dashboard/settings/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/settings') ? 'page' : undefined}
          >
            <span>{t('settings')}</span>
          </Link>
        )}

        {canViewAdmin && (
          <>
            <div className="dashboard-shell__nav-section">{t('adminSection')}</div>
            {[
              { href: '/dashboard/admin/users' as Route, label: t('admin.users') },
              { href: '/dashboard/admin/roles' as Route, label: t('admin.roles') },
              { href: '/dashboard/admin/permissions' as Route, label: t('admin.permissions') },
            ].map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </>
        )}
      </nav>
    </aside>
  );
}
