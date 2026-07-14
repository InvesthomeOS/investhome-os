'use client';

import { AuthProvider } from '@/lib/auth/auth-context';
import { NotificationProvider } from '@/lib/notifications/notification-context';

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
        <div className="dashboard-shell">
          <SidebarNav />
          <div className="dashboard-shell__content">{children}</div>
          <NotificationDrawer />
        </div>
      </NotificationProvider>
    </AuthProvider>
  );
}
