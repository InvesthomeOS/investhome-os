'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useCompanyBranding } from '@/lib/company/company-context';
import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

import { useSidebarCollapsed } from './use-sidebar-collapsed';

function moduleHref(module: ModuleName): Route {
  if (module === 'leads') {
    return '/dashboard/sales' as Route;
  }
  return `/dashboard/${module}` as Route;
}

const MODULE_PERMISSIONS: Record<ModuleName, { resource: string; action: string; fallback?: { resource: string; action: string } }> = {
  executive: { resource: 'executive', action: 'view' },
  leads: { resource: 'sales', action: 'view', fallback: { resource: 'leads', action: 'view' } },
  investors: { resource: 'investors', action: 'view' },
  projects: { resource: 'projects', action: 'view' },
  inventory: { resource: 'inventory', action: 'view' },
  finance: { resource: 'finance', action: 'view' },
};

export function SidebarNav() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tCommon = useTranslations('common');
  const { user, canViewAdmin } = useAuth();
  const { displayName, slogan } = useCompanyBranding();
  const [collapsed, toggleCollapsed] = useSidebarCollapsed();
  const canViewActivity = user ? hasPermission(user, 'activity', 'view') : false;
  const canViewDocuments = user ? hasPermission(user, 'documents', 'view') : false;
  const canViewDesign = user ? hasPermission(user, 'design', 'view') : false;
  const canViewSettings = user ? hasPermission(user, 'settings', 'view') || hasPermission(user, 'company', 'view') : false;

  const shellClass = collapsed
    ? 'dashboard-shell__sidebar dashboard-shell__sidebar--collapsed'
    : 'dashboard-shell__sidebar';

  return (
    <aside className={shellClass}>
      <div className="dashboard-shell__sidebar-top">
        <div className="dashboard-shell__brand">
          <Link href="/dashboard" className="dashboard-shell__brand-link">
            <span className="dashboard-shell__brand-mark" aria-hidden="true">
              IH
            </span>
            <span className="dashboard-shell__brand-text">
              <span className="dashboard-shell__brand-title">{displayName}</span>
              {!collapsed && (
                <span className="dashboard-shell__brand-subtitle">
                  {slogan ?? tCommon('operations')}
                </span>
              )}
            </span>
          </Link>
        </div>
        <button
          type="button"
          className="dashboard-shell__collapse"
          onClick={toggleCollapsed}
          aria-expanded={!collapsed}
          aria-label={collapsed ? t('expandSidebar') : t('collapseSidebar')}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      <nav className="dashboard-shell__nav" aria-label={t('ariaLabel')}>
        <div className="dashboard-shell__nav-section">{t('workspacesSection')}</div>
        {MODULE_NAMES.map((module) => {
          const permission = MODULE_PERMISSIONS[module];
          const allowed = user
            ? hasPermission(user, permission.resource, permission.action) ||
              (permission.fallback
                ? hasPermission(user, permission.fallback.resource, permission.fallback.action)
                : false)
            : false;
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
            module === 'inventory' ||
            module === 'finance';

          const navTitle =
            module === 'leads' ? t('modules.sales.title') : t(`modules.${module}.title`);

          return (
            <Link
              key={module}
              href={href}
              className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              title={collapsed ? navTitle : undefined}
            >
              <span className="dashboard-shell__nav-link-label">{navTitle}</span>
              {!collapsed && !isImplemented && (
                <span className="dashboard-shell__nav-badge">{tCommon('soon')}</span>
              )}
            </Link>
          );
        })}

        <div className="dashboard-shell__nav-section">{t('toolsSection')}</div>

        {canViewDocuments && (
          <Link
            href={'/dashboard/documents' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/documents' || pathname.startsWith('/dashboard/documents/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/documents') ? 'page' : undefined}
            title={collapsed ? t('documents') : undefined}
          >
            <span className="dashboard-shell__nav-link-label">{t('documents')}</span>
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
            title={collapsed ? t('designStudio') : undefined}
          >
            <span className="dashboard-shell__nav-link-label">{t('designStudio')}</span>
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
            title={collapsed ? t('activity') : undefined}
          >
            <span className="dashboard-shell__nav-link-label">{t('activity')}</span>
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
            title={collapsed ? t('settings') : undefined}
          >
            <span className="dashboard-shell__nav-link-label">{t('settings')}</span>
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
                  title={collapsed ? item.label : undefined}
                >
                  <span className="dashboard-shell__nav-link-label">{item.label}</span>
                </Link>
              );
            })}
          </>
        )}
      </nav>
    </aside>
  );
}
