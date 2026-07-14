'use client';

import { AuthProvider } from '@/lib/auth/auth-context';

import { SidebarNav } from './_components/sidebar-nav';

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <AuthProvider>
      <div className="dashboard-shell">
        <SidebarNav />
        <div className="dashboard-shell__content">{children}</div>
      </div>
    </AuthProvider>
  );
}
