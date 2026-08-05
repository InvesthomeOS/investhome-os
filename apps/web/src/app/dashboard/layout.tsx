'use client';

import { OsShell } from '@/components/shell/os-shell';

import { ScreenshotDashboardInteractionProvider } from './_components/screenshot-dashboard-interactions';

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ScreenshotDashboardInteractionProvider>
      <OsShell>{children}</OsShell>
    </ScreenshotDashboardInteractionProvider>
  );
}
