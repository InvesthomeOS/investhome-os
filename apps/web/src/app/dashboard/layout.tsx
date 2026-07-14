'use client';

import { AuthProvider } from '@/lib/auth/auth-context';
import { NotificationProvider } from '@/lib/notifications/notification-context';
import { GlobalSearchProvider } from '@/lib/search/global-search-context';

import { GlobalSearchPalette } from './_components/global-search-palette';
import { NotificationDrawer } from './_components/notification-drawer';
import { SidebarNav } from './_components/sidebar-nav';

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <AuthProvider>
      <NotificationProvider>
        <GlobalSearchProvider>
          <div className="dashboard-shell">
            <SidebarNav />
            <div className="dashboard-shell__content">{children}</div>
            <NotificationDrawer />
            <GlobalSearchPalette />
          </div>
        </GlobalSearchProvider>
      </NotificationProvider>
    </AuthProvider>
  );
}
