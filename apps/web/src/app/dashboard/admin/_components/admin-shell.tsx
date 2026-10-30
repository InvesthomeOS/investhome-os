'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMemo, type ReactNode } from 'react';

import { canViewRoles, canViewUsers, hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { visibleSettingsEntries, type SettingsEntry } from '@/lib/settings/settings-catalog';

type AdminNavItem = {
  href: Route;
  labelKey: string;
  match: (path: string) => boolean;
  visible: boolean;
};

type AdminNavGroup = {
  id: string;
  labelKey: string | null;
  items: AdminNavItem[];
};

function entryItem(entry: SettingsEntry): AdminNavItem {
  return {
    href: entry.href as Route,
    labelKey: entry.adminNavKey ?? entry.id,
    match: (path: string) => path === entry.href || path.startsWith(`${entry.href}/`),
    visible: true,
  };
}

export function AdminShell({ children }: { children: ReactNode }) {
  const t = useTranslations('adminShell');
  const tNav = useTranslations('navigation');
  const pathname = usePathname();
  const { user } = useAuth();

  const groups = useMemo<AdminNavGroup[]>(() => {
    const entries = visibleSettingsEntries(user);
    const canViewSecurity = hasPermission(user, 'security', 'view');
    const canViewActivity = hasPermission(user, 'activity', 'view');
    const canViewSettings = entries.some((entry) => entry.tab);
    const canPreview = Boolean(
      user && (canViewUsers(user) || canViewRoles(user) || canViewSecurity || canViewSettings),
    );

    const overview: AdminNavItem = {
      href: '/dashboard/admin' as Route,
      labelKey: 'overview',
      match: (path: string) => path === '/dashboard/admin',
      visible: Boolean(user && (canViewUsers(user) || canViewRoles(user) || canViewSecurity)),
    };
    const activity: AdminNavItem = {
      href: '/dashboard/activity' as Route,
      labelKey: 'activity',
      match: (path: string) => path.startsWith('/dashboard/activity'),
      visible: canViewActivity,
    };
    const platformSettings: AdminNavItem = {
      href: '/dashboard/settings' as Route,
      labelKey: 'platformSettings',
      match: (path: string) => path.startsWith('/dashboard/settings'),
      visible: canViewSettings,
    };

    return [
      { id: 'overview', labelKey: null, items: [overview].filter((item) => item.visible) },
      {
        id: 'access',
        labelKey: 'access',
        items: entries.filter((entry) => entry.group === 'access').map(entryItem),
      },
      {
        id: 'security',
        labelKey: 'security',
        items: entries.filter((entry) => entry.group === 'security').map(entryItem),
      },
      {
        id: 'platform',
        labelKey: 'platform',
        items: [
          platformSettings,
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
          activity,
        ].filter((item) => item.visible),
      },
      {
        id: 'previews',
        labelKey: 'previews',
        items: [
          {
            href: '/dashboard/admin/design-system' as Route,
            labelKey: 'designSystem',
            match: (path: string) => path.startsWith('/dashboard/admin/design-system'),
            visible: canPreview,
          },
          {
            href: '/dashboard/admin/tailadmin-preview' as Route,
            labelKey: 'tailadminPreview',
            match: (path: string) => path.startsWith('/dashboard/admin/tailadmin-preview'),
            visible: canPreview,
          },
          {
            href: '/dashboard/admin/github-ui-preview' as Route,
            labelKey: 'githubUiPreview',
            match: (path: string) => path.startsWith('/dashboard/admin/github-ui-preview'),
            visible: canPreview,
          },
        ].filter((item) => item.visible),
      },
    ].filter((group) => group.items.length > 0);
  }, [user]);

  const navLabelKeys = new Set(['users', 'roles', 'permissions']);

  return (
    <div className="admin-shell">
      <nav className="admin-shell__nav" aria-label={t('navLabel')}>
        {groups.map((group) => (
          <div key={group.id} className="admin-shell__nav-group">
            {group.labelKey ? (
              <p className="admin-shell__nav-section">{t(`sections.${group.labelKey}`)}</p>
            ) : null}
            <ol className="admin-shell__nav-list">
              {group.items.map((item) => {
                const isActive = item.match(pathname);
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
          </div>
        ))}
      </nav>
      {children}
    </div>
  );
}
