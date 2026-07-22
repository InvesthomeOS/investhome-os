'use client';

import { OsShell } from '@/components/shell/os-shell';

import { CompanySidebar } from './_components/company-sidebar';
import { CompanyToastProvider, CompanyToastStack } from './_components/use-company-toast';

import './company.css';

export default function CompanyLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <OsShell withQueryProvider shellClassName="company-shell" workspaceChrome={<CompanySidebar />}>
      <CompanyToastProvider>
        {children}
        <CompanyToastStack />
      </CompanyToastProvider>
    </OsShell>
  );
}
