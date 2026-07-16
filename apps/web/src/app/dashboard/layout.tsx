'use client';

import { AuthProvider } from '@/lib/auth/auth-context';
import { CompanyBrandingProvider } from '@/lib/company/company-context';
import { NotificationProvider } from '@/lib/notifications/notification-context';
import { GlobalSearchProvider } from '@/lib/search/global-search-context';
import { BrandThemeInjector } from '@/lib/theme/brand-theme-injector';
import { ThemeProvider } from '@/lib/theme/theme-context';

import { AppHeader } from './_components/app-header';
import { GlobalSearchPalette } from './_components/global-search-palette';
import { NotificationDrawer } from './_components/notification-drawer';
import { SidebarNav } from './_components/sidebar-nav';

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <CompanyBrandingProvider>
          <BrandThemeInjector />
          <NotificationProvider>
            <GlobalSearchProvider>
              <div className="dashboard-shell">
                <SidebarNav />
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
}
