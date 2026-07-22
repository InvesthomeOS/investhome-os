'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

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

export function SidebarNav() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tCommon = useTranslations('common');
  const { user, canViewAdmin } = useAuth();
  const { displayName } = useCompanyBranding();
  const [collapsed, toggleCollapsed] = useSidebarCollapsed();
  const canViewActivity = user ? hasPermission(user, 'activity', 'view') : false;
  const canViewKnowledge =
    user
      ? hasPermission(user, 'knowledge', 'view') || hasPermission(user, 'documents', 'view')
      : false;
  const canViewAi = canViewAiWorkspace(user);
  const canViewBi = canViewAnalytics(user);
  const canViewAutomationCenter = canViewAutomation(user);
  const canViewDesign = user ? hasPermission(user, 'design', 'view') : false;
  const canViewSettings =
    user ? hasPermission(user, 'settings', 'view') || hasPermission(user, 'company', 'view') : false;
  const operationalWorkspaces = getVisibleWorkspaces(user);

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
              data-tour={tourAttr}
            >
              <span className="dashboard-shell__nav-link-icon">
                <IhIcon name={MODULE_ICONS[module]} size="nav" />
              </span>
              <span className="dashboard-shell__nav-link-label">{navTitle}</span>
              {!collapsed && !isImplemented && (
                <span className="dashboard-shell__nav-badge">{tCommon('soon')}</span>
              )}
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

        {canViewBi && (
          <Link
            href={'/dashboard/analytics' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/analytics' || pathname.startsWith('/dashboard/analytics/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/analytics') ? 'page' : undefined}
            title={collapsed ? t('businessIntelligence') : undefined}
          >
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="barChart" size="nav" />
            </span>
            <span className="dashboard-shell__nav-link-label">{t('businessIntelligence')}</span>
          </Link>
        )}

        <Link
          href={'/dashboard/onboarding' as Route}
          className={`dashboard-shell__nav-link${
            pathname === '/dashboard/onboarding' || pathname.startsWith('/dashboard/onboarding/')
              ? ' dashboard-shell__nav-link--active'
              : ''
          }`}
          aria-current={pathname.startsWith('/dashboard/onboarding') ? 'page' : undefined}
          title={collapsed ? t('onboarding') : undefined}
          data-testid="os-nav-onboarding"
          data-tour="nav-onboarding"
        >
          <span className="dashboard-shell__nav-link-icon">
            <IhIcon name="target" size="nav" />
          </span>
          <span className="dashboard-shell__nav-link-label">{t('onboarding')}</span>
        </Link>

        <Link
          href={'/dashboard/training' as Route}
          className={`dashboard-shell__nav-link${
            pathname === '/dashboard/training' || pathname.startsWith('/dashboard/training/')
              ? ' dashboard-shell__nav-link--active'
              : ''
          }`}
          aria-current={pathname.startsWith('/dashboard/training') ? 'page' : undefined}
          title={collapsed ? t('training') : undefined}
          data-testid="os-nav-training"
          data-tour="nav-training"
        >
          <span className="dashboard-shell__nav-link-icon">
            <IhIcon name="check" size="nav" />
          </span>
          <span className="dashboard-shell__nav-link-label">{t('training')}</span>
        </Link>

        <Link
          href={'/dashboard/help' as Route}
          className={`dashboard-shell__nav-link${
            pathname === '/dashboard/help' || pathname.startsWith('/dashboard/help/')
              ? ' dashboard-shell__nav-link--active'
              : ''
          }`}
          aria-current={pathname.startsWith('/dashboard/help') ? 'page' : undefined}
          title={collapsed ? t('help') : undefined}
          data-testid="os-nav-help"
          data-tour="nav-help"
        >
          <span className="dashboard-shell__nav-link-icon">
            <IhIcon name="inbox" size="nav" />
          </span>
          <span className="dashboard-shell__nav-link-label">{t('help')}</span>
        </Link>

        {canViewAi && (
          <Link
            href={'/dashboard/ai' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/ai' || pathname.startsWith('/dashboard/ai/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/ai') ? 'page' : undefined}
            title={collapsed ? t('aiWorkspace') : undefined}
          >
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="sparkles" size="nav" />
            </span>
            <span className="dashboard-shell__nav-link-label">{t('aiWorkspace')}</span>
          </Link>
        )}

        {canViewKnowledge && (
          <Link
            href={'/dashboard/knowledge' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/knowledge' ||
              pathname.startsWith('/dashboard/knowledge/') ||
              pathname === '/dashboard/documents' ||
              pathname.startsWith('/dashboard/documents/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={
              pathname.startsWith('/dashboard/knowledge') || pathname.startsWith('/dashboard/documents')
                ? 'page'
                : undefined
            }
            title={collapsed ? t('knowledgeHub') : undefined}
          >
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="documents" size="nav" />
            </span>
            <span className="dashboard-shell__nav-link-label">{t('knowledgeHub')}</span>
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
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="design" size="nav" />
            </span>
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
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="activity" size="nav" />
            </span>
            <span className="dashboard-shell__nav-link-label">{t('activity')}</span>
          </Link>
        )}

        {canViewAutomationCenter && (
          <Link
            href={'/dashboard/automation' as Route}
            className={`dashboard-shell__nav-link${
              pathname === '/dashboard/automation' || pathname.startsWith('/dashboard/automation/')
                ? ' dashboard-shell__nav-link--active'
                : ''
            }`}
            aria-current={pathname.startsWith('/dashboard/automation') ? 'page' : undefined}
            title={collapsed ? t('automation') : undefined}
          >
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="refresh" size="nav" />
            </span>
            <span className="dashboard-shell__nav-link-label">{t('automation')}</span>
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
            <span className="dashboard-shell__nav-link-icon">
              <IhIcon name="settings" size="nav" />
            </span>
            <span className="dashboard-shell__nav-link-label">{t('settings')}</span>
          </Link>
        )}

        {canViewAdmin && (
          <>
            <div className="dashboard-shell__nav-section">{t('adminSection')}</div>
            {(
              [
                { href: '/dashboard/admin' as Route, label: t('adminSection'), icon: 'admin' as const, tour: undefined },
                { href: '/dashboard/admin/users' as Route, label: t('admin.users'), icon: 'users' as const, tour: undefined },
                { href: '/dashboard/admin/roles' as Route, label: t('admin.roles'), icon: 'roles' as const, tour: undefined },
                {
                  href: '/dashboard/admin/permissions' as Route,
                  label: t('admin.permissions'),
                  icon: 'permissions' as const,
                  tour: undefined,
                },
                {
                  href: '/dashboard/admin/adoption' as Route,
                  label: t('admin.adoption'),
                  icon: 'barChart' as const,
                  tour: 'nav-admin-adoption',
                },
                {
                  href: '/dashboard/admin/training-builder' as Route,
                  label: t('admin.trainingBuilder'),
                  icon: 'design' as const,
                  tour: 'nav-training-builder',
                },
                {
                  href: '/dashboard/admin/operations' as Route,
                  label: t('admin.operations'),
                  icon: 'activity' as const,
                  tour: 'nav-operations',
                },
                {
                  href: '/dashboard/admin/data-platform' as Route,
                  label: t('admin.dataPlatform'),
                  icon: 'barChart' as const,
                  tour: undefined,
                },
                {
                  href: '/dashboard/admin/metric-catalog' as Route,
                  label: t('admin.metricCatalog'),
                  icon: 'barChart' as const,
                  tour: undefined,
                },
              ] as const
            ).map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href === ('/dashboard/admin' as Route) && pathname === '/dashboard/admin') ||
                (item.href !== ('/dashboard/admin' as Route) && pathname.startsWith(`${item.href}/`));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`dashboard-shell__nav-link${isActive ? ' dashboard-shell__nav-link--active' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                  title={collapsed ? item.label : undefined}
                  data-tour={item.tour}
                >
                  <span className="dashboard-shell__nav-link-icon">
                    <IhIcon name={item.icon} size="nav" />
                  </span>
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
