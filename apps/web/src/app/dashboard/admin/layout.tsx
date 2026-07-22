'use client';

import type { ReactNode } from 'react';

import { AdminShell } from './_components/admin-shell';
import { AdminToastStack } from './_components/admin-toast-stack';
import { AdminToastProvider } from './_components/use-admin-toast';

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <AdminToastProvider>
      <AdminShell>{children}</AdminShell>
      <AdminToastStack />
    </AdminToastProvider>
  );
}
