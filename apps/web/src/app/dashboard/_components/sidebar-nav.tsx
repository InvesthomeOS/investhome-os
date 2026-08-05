'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canViewAiWorkspace } from '@/lib/ai/ai-permissions';
import { canViewAnalytics } from '@/lib/analytics/bi-permissions';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useCompanyBranding } from '@/lib/company/company-context';
import { getVisibleWorkspaces, isWorkspaceRouteActive } from '@/lib/workspaces/workspace-registry';
import { MODULE_NAMES, type ModuleName } from '@investhome/shared';

import { WorkspaceSidebarBrand } from '@/components/shell/workspace-sidebar-brand';
import { canViewAutomation } from '@/lib/automation/automation-permissions';
import { canReadMarketing } from '@/lib/marketing/marketing-permissions';

import { useSidebarCollapsed } from './use-sidebar-collapsed';

function moduleHref(module: ModuleName): Route {
  if (module === 'leads') {
    return '/dashboard/sales' as Route;
  }
  return `/dashboard/${module}` as Route;
}

const MODULE_PERMISSIONS: Record<
  ModuleName,
  { resource: string; action: string; fallback?: { resource: string; action: string } }
> = {
  executive: { resource: 'executive', action: 'view' },
  leads: { resource: 'sales', action: 'view', fallback: { resource: 'leads', action: 'view' } },
  investors: { resource: 'investors', action: 'view' },
  projects: { resource: 'projects', action: 'view' },
  inventory: { resource: 'inventory', action: 'view' },
  finance: { resource: 'finance', action: 'view' },
};

const MODULE_ICONS: Record<ModuleName, IhIconName> = {
  executive: 'executive',
  leads: 'sales',
  investors: 'investors',
  projects: 'projects',
  inventory: 'inventory',
  finance: 'finance',
};

const WORKSPACE_ICONS: Record<string, IhIconName> = {
  crm: 'crm',
  marketing: 'marketing',
  company: 'executive',
};

type NavLinkItem = {
  href: Route;
  label: string;
  icon: IhIconName;
  tour?: string;
  testId?: string;
};

function pathMatches(pathname: string, href: string, exactRoot = false): boolean {
  if (pathname === href) return true;
  if (exactRoot) return false;
  return pathname.startsWith(`${href}/`);
}

function NavLink({
  item,
  pathname,
  collapsed,
  exactRoot = false,
  child = false,
}: {
  item: NavLinkItem;
  pathname: string;
  collapsed: boolean;
  exactRoot?: boolean;
  child?: boolean;
}) {
  const isActive = pathMatches(pathname, item.href, exactRoot);
  return (
    <Link
      href={item.href}
      className={`dashboard-shell__nav-link${child ? ' dashboard-shell__nav-link--child' : ''}${
        isActive ? ' dashboard-shell__nav-link--active' : ''
      }`}
      aria-current={isActive ? 'page' : undefined}
      title={collapsed ? item.label : undefined}
      data-tour={item.tour}
      data-testid={item.testId}
    >
      <span className="dashboard-shell__nav-link-icon">
        <IhIcon name={item.icon} size="nav" />
      </span>
      <span className="dashboard-shell__nav-link-label">{item.label}</span>
    </Link>
  );
}

function NavGroup({
  id,
  label,
  icon,
  collapsed,
  open,
  onToggle,
  active,
  children,
}: {
  id: string;
  label: string;
  icon: IhIconName;
  collapsed: boolean;
  open: boolean;
  onToggle: () => void;
  active: boolean;
  children: ReactNode;
}) {
  return (
    <div className="dashboard-shell__nav-group" data-nav-group={id}>
      <button
        type="button"
        className={`dashboard-shell__nav-group-toggle${active ? ' dashboard-shell__nav-group-toggle--active' : ''}`}
        aria-expanded={open}
        aria-controls={`os-nav-group-${id}`}
        onClick={onToggle}
        title={collapsed ? label : undefined}
      >
        <span className="dashboard-shell__nav-link-icon">
          <IhIcon name={icon} size="nav" />
        </span>
        <span className="dashboard-shell__nav-link-label">{label}</span>
        {!collapsed && (
          <span className="dashboard-shell__nav-group-chevron" aria-hidden="true">
            <IhIcon name={open ? 'chevronDown' : 'chevronRight'} size={14} />
          </span>
        )}
      </button>
      {open ? (
        <div id={`os-nav-group-${id}`} className="dashboard-shell__nav-submenu" role="group" aria-label={label}>
          {children}
        </div>
      ) : null}
    </div>
  );
}

/** Unified OS sidebar map — one StandardSidebarNav for all OsShell routes including /dashboard. */
export function SidebarNav() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const { user, canViewAdmin } = useAuth();
  const { displayName } = useCompanyBranding();
  const [collapsed, toggleCollapsed] = useSidebarCollapsed();
  const canViewAi = canViewAiWorkspace(user);
  const canViewBi = canViewAnalytics(user);
  const canViewAutomationCenter = canViewAutomation(user);
  const canViewCreativeStudio = canReadMarketing(user);
  const canViewSettings =
    user ? hasPermission(user, 'settings', 'view') || hasPermission(user, 'company', 'view') : false;
  const operationalWorkspaces = getVisibleWorkspaces(user);

  const identityChildren: NavLinkItem[] = [
    { href: '/dashboard/admin/users' as Route, label: t('admin.users'), icon: 'users' },
    { href: '/dashboard/admin/roles' as Route, label: t('admin.roles'), icon: 'roles' },
    {
      href: '/dashboard/admin/permissions' as Route,
      label: t('admin.permissions'),
      icon: 'permissions',
    },
  ];

  const platformChildren: NavLinkItem[] = [
    {
      href: '/dashboard/admin/operations' as Route,
      label: t('admin.operations'),
      icon: 'activity',
      tour: 'nav-operations',
    },
    {
      href: '/dashboard/admin/data-platform' as Route,
      label: t('admin.dataPlatform'),
      icon: 'barChart',
    },
    {
      href: '/dashboard/admin/metric-catalog' as Route,
      label: t('admin.metricCatalog'),
      icon: 'barChart',
    },
    {
      href: '/dashboard/admin/adoption' as Route,
      label: t('admin.adoption'),
      icon: 'barChart',
      tour: 'nav-admin-adoption',
    },
  ];

  const identityActive = identityChildren.some((item) => pathMatches(pathname, item.href));
  const platformActive = platformChildren.some((item) => pathMatches(pathname, item.href));

  const [identityOpen, setIdentityOpen] = useState(identityActive);
  const [platformOpen, setPlatformOpen] = useState(platformActive);

  useEffect(() => {
    if (identityActive) setIdentityOpen(true);
  }, [identityActive]);

  useEffect(() => {
    if (platformActive) setPlatformOpen(true);
  }, [platformActive]);

  const shellClass = collapsed
    ? 'dashboard-shell__sidebar dashboard-shell__sidebar--collapsed'
    : 'dashboard-shell__sidebar';

  const homeActive = pathname === '/dashboard';

  return (
    <aside className={shellClass}>
      <WorkspaceSidebarBrand
        href="/dashboard"
        collapsed={collapsed}
        ariaLabel={displayName}
        onToggleCollapsed={toggleCollapsed}
        expandLabel={t('expandSidebar')}
        collapseLabel={t('collapseSidebar')}
      />

      <nav className="dashboard-shell__nav" aria-label={t('ariaLabel')}>
        <div className="dashboard-shell__nav-section">{t('commandSection')}</div>
        <Link
          href={'/dashboard' as Route}
          className={`dashboard-shell__nav-link${homeActive ? ' dashboard-shell__nav-link--active' : ''}`}
          aria-current={homeActive ? 'page' : undefined}
          title={collapsed ? t('mainMenu') : undefined}
          data-testid="os-main-menu"
          data-tour="os-main-menu"
        >
          <span className="dashboard-shell__nav-link-icon">
            <IhIcon name="home" size="nav" />
          </span>
          <span className="dashboard-shell__nav-link-label">{t('mainMenu')}</span>
        </Link>

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
          const tourAttr =
            module === 'executive'
              ? 'nav-executive'
              : module === 'investors'
                ? 'nav-investors'
                : module === 'projects'
                  ? 'nav-projects'
                  : module === 'finance'
                    ? 'nav-finance'
                    : undefined;

          const href = moduleHref(module);
          const isActive = pathname === href || pathname.startsWith(`${href}/`);
          const navTitle =
            module === 'leads' ? t('modules.sales.title') : t(`modules.${module}.title`);

          return (
            <Link
              key={module}
              href={href}
              className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              title={collapsed ? navTitle : undefined}
              data-tour={tourAttr}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={MODULE_ICONS[module]} size="nav" />
              </span>
              <span className="dashboard-shell__nav-link-label">{navTitle}</span>
            </Link>
          );
        })}

        {operationalWorkspaces.map((workspace) => {
          const href = workspace.route;
          const isActive = isWorkspaceRouteActive(pathname, workspace);
          const navTitle = t(
            workspace.labelKey as 'modules.crm.title' | 'modules.marketing.title' | 'modules.company.title',
          );
          const icon = WORKSPACE_ICONS[workspace.id] ?? 'executive';

          return (
            <Link
              key={workspace.id}
              href={href}
              className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
              aria-current={isActive ? 'page' : undefined}
              title={collapsed ? navTitle : undefined}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={icon} size="nav" />
              </span>
              <span className="dashboard-shell__nav-link-label">{navTitle}</span>
            </Link>
          );
        })}

        <div className="dashboard-shell__nav-section">{t('toolsSection')}</div>

        {canViewCreativeStudio && (
          <NavLink
            pathname={pathname}
            collapsed={collapsed}
            item={{
              href: '/workspaces/creative-studio' as Route,
              label: t('creativeStudio'),
              icon: 'design',
              testId: 'os-nav-creative-studio',
            }}
          />
        )}

        {canViewBi && (
          <NavLink
            pathname={pathname}
            collapsed={collapsed}
            item={{
              href: '/dashboard/analytics' as Route,
              label: t('businessIntelligence'),
              icon: 'barChart',
            }}
          />
        )}

        {canViewAi && (
          <NavLink
            pathname={pathname}
            collapsed={collapsed}
            item={{
              href: '/dashboard/ai' as Route,
              label: t('aiWorkspace'),
              icon: 'sparkles',
            }}
          />
        )}

        <NavLink
          pathname={pathname}
          collapsed={collapsed}
          item={{
            href: '/dashboard/training' as Route,
            label: t('training'),
            icon: 'check',
            testId: 'os-nav-training',
            tour: 'nav-training',
          }}
        />

        {canViewAutomationCenter && (
          <NavLink
            pathname={pathname}
            collapsed={collapsed}
            item={{
              href: '/dashboard/automation' as Route,
              label: t('automation'),
              icon: 'refresh',
            }}
          />
        )}

        <NavLink
          pathname={pathname}
          collapsed={collapsed}
          item={{
            href: '/dashboard/help' as Route,
            label: t('help'),
            icon: 'inbox',
            testId: 'os-nav-help',
            tour: 'nav-help',
          }}
        />

        {(canViewSettings || canViewAdmin) && (
          <>
            <div className="dashboard-shell__nav-section">{t('adminSection')}</div>

            {canViewAdmin && (
              <NavLink
                pathname={pathname}
                collapsed={collapsed}
                exactRoot
                item={{
                  href: '/dashboard/admin' as Route,
                  label: t('adminSection'),
                  icon: 'admin',
                }}
              />
            )}

            {canViewSettings && (
              <NavLink
                pathname={pathname}
                collapsed={collapsed}
                item={{
                  href: '/dashboard/settings' as Route,
                  label: t('settings'),
                  icon: 'settings',
                }}
              />
            )}

            {canViewAdmin && (
              <>
                <NavGroup
                  id="identity"
                  label={t('identityAccess')}
                  icon="users"
                  collapsed={collapsed}
                  open={identityOpen}
                  onToggle={() => setIdentityOpen((value) => !value)}
                  active={identityActive}
                >
                  {identityChildren.map((item) => (
                    <NavLink key={item.href} item={item} pathname={pathname} collapsed={collapsed} child />
                  ))}
                </NavGroup>

                <NavGroup
                  id="platform"
                  label={t('platform')}
                  icon="activity"
                  collapsed={collapsed}
                  open={platformOpen}
                  onToggle={() => setPlatformOpen((value) => !value)}
                  active={platformActive}
                >
                  {platformChildren.map((item) => (
                    <NavLink key={item.href} item={item} pathname={pathname} collapsed={collapsed} child />
                  ))}
                </NavGroup>
              </>
            )}
          </>
        )}
      </nav>
    </aside>
  );
}
