'use client';

import { OsShell } from '@/components/shell/os-shell';

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <OsShell>{children}</OsShell>;
}
