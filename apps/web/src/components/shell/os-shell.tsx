'use client';

import type { ReactNode } from 'react';
import { usePathname } from 'next/navigation';

import { AiShellHost } from '@/components/ai/ai-shell-host';
import { AppHeader } from '@/app/dashboard/_components/app-header';
import { GlobalSearchPalette } from '@/app/dashboard/_components/global-search-palette';
import { NotificationDrawer } from '@/app/dashboard/_components/notification-drawer';
import { ScreenshotDashboardPreferencesProvider } from '@/app/dashboard/_components/screenshot-dashboard-preferences';
import { SidebarNav } from '@/app/dashboard/_components/sidebar-nav';
import { AuthProvider } from '@/lib/auth/auth-context';
import { CompanyBrandingProvider } from '@/lib/company/company-context';
import { NotificationProvider } from '@/lib/notifications/notification-context';
import { QueryProvider } from '@/lib/query/query-provider';
import { GlobalSearchProvider } from '@/lib/search/global-search-context';
import { BrandThemeInjector } from '@/lib/theme/brand-theme-injector';
import { DS_VERSION_V2, isDsV2ShellRoute } from '@/lib/theme/ds-version';
import { ThemeProvider } from '@/lib/theme/theme-context';

type OsShellProps = {
  children: ReactNode;
  /** Optional workspace-specific chrome rendered inside the content column (secondary nav). */
  workspaceChrome?: ReactNode;
  shellClassName?: string;
  withQueryProvider?: boolean;
};

/**
 * Unified Investhome OS shell — main sidebar + global header for all authenticated workspaces.
 * CRM / Marketing / Company keep domain secondary nav via `workspaceChrome`, not isolated shells.
 *
 * UXR1 V2 Phase 2A: opt-in `data-ds-version="v2"` only on Dashboard home + Executive routes.
 */
export function OsShell({
  children,
  workspaceChrome,
  shellClassName,
  withQueryProvider = false,
}: OsShellProps) {
  const pathname = usePathname();
  const dsV2 = isDsV2ShellRoute(pathname);
  const shellClass = [
    'dashboard-shell',
    dsV2 ? 'dashboard-shell--v2' : '',
    pathname === '/dashboard' ? 'dashboard-shell--home' : '',
    shellClassName,
  ]
    .filter(Boolean)
    .join(' ');

  const shell = (
    <AiShellHost>
      <div
        className={shellClass}
        data-ds-version={dsV2 ? DS_VERSION_V2 : undefined}
        data-testid={dsV2 ? 'os-shell-v2' : 'os-shell'}
      >
        <SidebarNav />
        <div className="dashboard-shell__main">
          <AppHeader />
          {workspaceChrome ? (
            <div className="os-workspace-chrome">
              {workspaceChrome}
              <div className="dashboard-shell__content os-workspace-chrome__content">{children}</div>
            </div>
          ) : (
            <div className="dashboard-shell__content">{children}</div>
          )}
        </div>
        <NotificationDrawer />
        <GlobalSearchPalette />
      </div>
    </AiShellHost>
  );

  const body = (
    <CompanyBrandingProvider>
      <BrandThemeInjector />
      <NotificationProvider>
        <GlobalSearchProvider>
          {pathname === '/dashboard' ? (
            <ScreenshotDashboardPreferencesProvider>{shell}</ScreenshotDashboardPreferencesProvider>
          ) : (
            shell
          )}
        </GlobalSearchProvider>
      </NotificationProvider>
    </CompanyBrandingProvider>
  );

  return (
    <ThemeProvider>
      <AuthProvider>
        {withQueryProvider ? <QueryProvider>{body}</QueryProvider> : body}
      </AuthProvider>
    </ThemeProvider>
  );
}
