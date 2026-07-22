'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMemo, type ReactNode } from 'react';

import { canViewRoles, canViewUsers, hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

type AdminNavItem = {
  href: Route;
  labelKey: string;
  match: (path: string, activeTab: string | null) => boolean;
  visible: boolean;
};

export function AdminShell({ children }: { children: ReactNode }) {
  const t = useTranslations('adminShell');
  const tNav = useTranslations('navigation');
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const tab = searchParams.get('tab');
  const { user } = useAuth();

  const navItems = useMemo<AdminNavItem[]>(() => {
    const canViewCompany = hasPermission(user, 'company', 'view');
    const canViewOffices = hasPermission(user, 'offices', 'view');
    const canViewOrganization = hasPermission(user, 'organization', 'view');
    const canViewActivity = hasPermission(user, 'activity', 'view');
    const canViewSecurity = hasPermission(user, 'security', 'view');
    const canViewSettings =
      hasPermission(user, 'settings', 'view') || canViewCompany || canViewOffices || canViewOrganization;

    const items: AdminNavItem[] = [
      {
        href: '/dashboard/admin' as Route,
        labelKey: 'overview',
        match: (path: string) => path === '/dashboard/admin',
        visible: Boolean(user && (canViewUsers(user) || canViewRoles(user) || canViewSecurity)),
      },
      {
        href: '/dashboard/admin/users' as Route,
        labelKey: 'users',
        match: (path: string) => path.startsWith('/dashboard/admin/users'),
        visible: Boolean(user && canViewUsers(user)),
      },
      {
        href: '/dashboard/admin/teams' as Route,
        labelKey: 'teams',
        match: (path: string) => path.startsWith('/dashboard/admin/teams'),
        visible: canViewOrganization || canViewCompany,
      },
      {
        href: '/dashboard/admin/roles' as Route,
        labelKey: 'roles',
        match: (path: string) => path.startsWith('/dashboard/admin/roles'),
        visible: Boolean(user && canViewRoles(user)),
      },
      {
        href: '/dashboard/admin/permissions' as Route,
        labelKey: 'permissions',
        match: (path: string) => path.startsWith('/dashboard/admin/permissions'),
        visible: Boolean(user && canViewRoles(user)),
      },
      {
        href: '/dashboard/admin/security' as Route,
        labelKey: 'security',
        match: (path: string) => path.startsWith('/dashboard/admin/security'),
        visible: canViewSecurity,
      },
      {
        href: '/dashboard/admin/authentication' as Route,
        labelKey: 'authentication',
        match: (path: string) => path.startsWith('/dashboard/admin/authentication'),
        visible: canViewSecurity,
      },
      {
        href: '/dashboard/admin/sessions' as Route,
        labelKey: 'sessions',
        match: (path: string) => path.startsWith('/dashboard/admin/sessions'),
        visible: canViewSecurity,
      },
      {
        href: '/dashboard/admin/api-keys' as Route,
        labelKey: 'apiKeys',
        match: (path: string) => path.startsWith('/dashboard/admin/api-keys'),
        visible: canViewSecurity,
      },
      {
        href: '/dashboard/admin/secrets' as Route,
        labelKey: 'secrets',
        match: (path: string) => path.startsWith('/dashboard/admin/secrets'),
        visible: canViewSecurity,
      },
      {
        href: '/dashboard/admin/audit' as Route,
        labelKey: 'audit',
        match: (path: string) => path.startsWith('/dashboard/admin/audit'),
        visible: canViewActivity || canViewSecurity,
      },
      {
        href: '/dashboard/admin/compliance' as Route,
        labelKey: 'compliance',
        match: (path: string) => path.startsWith('/dashboard/admin/compliance'),
        visible: canViewSecurity || hasPermission(user, 'compliance', 'view'),
      },
      {
        href: '/dashboard/admin/incidents' as Route,
        labelKey: 'incidents',
        match: (path: string) => path.startsWith('/dashboard/admin/incidents'),
        visible: canViewSecurity,
      },
      {
        href: '/dashboard/admin/platform' as Route,
        labelKey: 'platform',
        match: (path: string) => path.startsWith('/dashboard/admin/platform'),
        visible:
          canViewSecurity ||
          hasPermission(user, 'platform', 'view') ||
          hasPermission(user, 'platform', 'manage'),
      },
      {
        href: '/dashboard/admin/system' as Route,
        labelKey: 'system',
        match: (path: string) => path.startsWith('/dashboard/admin/system'),
        visible: canViewSecurity || canViewSettings,
      },
      {
        href: '/dashboard/admin/launch-health' as Route,
        labelKey: 'launchHealth',
        match: (path: string) => path.startsWith('/dashboard/admin/launch-health'),
        visible: canViewSecurity || canViewSettings,
      },
      {
        href: '/dashboard/admin/design-system' as Route,
        labelKey: 'designSystem',
        match: (path: string) => path.startsWith('/dashboard/admin/design-system'),
        visible: Boolean(user && (canViewUsers(user) || canViewRoles(user) || canViewSecurity || canViewSettings)),
      },
      {
        href: '/dashboard/admin/tailadmin-preview' as Route,
        labelKey: 'tailadminPreview',
        match: (path: string) => path.startsWith('/dashboard/admin/tailadmin-preview'),
        visible: Boolean(user && (canViewUsers(user) || canViewRoles(user) || canViewSecurity || canViewSettings)),
      },
      {
        href: '/dashboard/admin/github-ui-preview' as Route,
        labelKey: 'githubUiPreview',
        match: (path: string) => path.startsWith('/dashboard/admin/github-ui-preview'),
        visible: Boolean(user && (canViewUsers(user) || canViewRoles(user) || canViewSecurity || canViewSettings)),
      },
      {
        href: '/dashboard/settings?tab=company' as Route,
        labelKey: 'company',
        match: (path: string, activeTab: string | null) =>
          path.startsWith('/dashboard/settings') && activeTab === 'company',
        visible: canViewCompany,
      },
      {
        href: '/dashboard/settings?tab=offices' as Route,
        labelKey: 'offices',
        match: (path: string, activeTab: string | null) =>
          path.startsWith('/dashboard/settings') && activeTab === 'offices',
        visible: canViewOffices,
      },
      {
        href: '/dashboard/settings?tab=organization' as Route,
        labelKey: 'organization',
        match: (path: string, activeTab: string | null) =>
          path.startsWith('/dashboard/settings') && activeTab === 'organization',
        visible: canViewOrganization,
      },
      {
        href: '/dashboard/activity' as Route,
        labelKey: 'activity',
        match: (path: string) => path.startsWith('/dashboard/activity'),
        visible: canViewActivity,
      },
      {
        href: '/dashboard/settings?tab=notifications' as Route,
        labelKey: 'notifications',
        match: (path: string, activeTab: string | null) =>
          path.startsWith('/dashboard/settings') && activeTab === 'notifications',
        visible: canViewSettings,
      },
      {
        href: '/dashboard/settings' as Route,
        labelKey: 'settings',
        match: (path: string, activeTab: string | null) =>
          path.startsWith('/dashboard/settings') &&
          (!activeTab || !['company', 'offices', 'organization', 'notifications'].includes(activeTab)),
        visible: canViewSettings,
      },
    ];
    return items.filter((item) => item.visible);
  }, [user]);

  const navLabelKeys = new Set([
    'users',
    'roles',
    'permissions',
  ]);

  return (
    <div className="admin-shell">
      <nav className="admin-shell__nav" aria-label={t('navLabel')}>
        <ol className="admin-shell__nav-list">
          {navItems.map((item) => {
            const isActive = item.match(pathname, tab);
            const label = navLabelKeys.has(item.labelKey)
              ? tNav(`admin.${item.labelKey}` as 'admin.users')
              : t(`nav.${item.labelKey}` as 'nav.users');
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`admin-shell__nav-link${isActive ? ' admin-shell__nav-link--active' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  {label}
                </Link>
              </li>
            );
          })}
        </ol>
      </nav>
      {children}
    </div>
  );
}
