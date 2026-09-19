'use client';

import type { ReactNode } from 'react';

import { AppHeader } from '@/app/dashboard/_components/app-header';
import { GlobalSearchPalette } from '@/app/dashboard/_components/global-search-palette';
import { NotificationDrawer } from '@/app/dashboard/_components/notification-drawer';
import { SidebarNav } from '@/app/dashboard/_components/sidebar-nav';
import { AuthProvider } from '@/lib/auth/auth-context';
import { CompanyBrandingProvider } from '@/lib/company/company-context';
import { NotificationProvider } from '@/lib/notifications/notification-context';
import { QueryProvider } from '@/lib/query/query-provider';
import { GlobalSearchProvider } from '@/lib/search/global-search-context';
import { BrandThemeInjector } from '@/lib/theme/brand-theme-injector';
import { ThemeProvider } from '@/lib/theme/theme-context';

type OsShellProps = {
  children: ReactNode;
  withQueryProvider?: boolean;
  shellClassName?: string;
  workspaceChrome?: ReactNode;
};

/** Workspace shell for CRM. Does not mount the AI host. */
export function OsShell({
  children,
  withQueryProvider = false,
  shellClassName,
  workspaceChrome,
}: OsShellProps) {
  const inner = (
    <ThemeProvider>
      <AuthProvider>
        <CompanyBrandingProvider>
          <BrandThemeInjector />
          <NotificationProvider>
            <GlobalSearchProvider>
              <div className={shellClassName ? `dashboard-shell ${shellClassName}` : 'dashboard-shell'}>
                {workspaceChrome ?? <SidebarNav />}
                <div className="dashboard-shell__main">
                  <AppHeader />
                  <div className="dashboard-shell__content">{children}</div>
                </div>
                <NotificationDrawer />
                <GlobalSearchPalette />
              </div>
            </GlobalSearchProvider>
          </NotificationProvider>
        </CompanyBrandingProvider>
      </AuthProvider>
    </ThemeProvider>
  );

  return withQueryProvider ? <QueryProvider>{inner}</QueryProvider> : inner;
}
