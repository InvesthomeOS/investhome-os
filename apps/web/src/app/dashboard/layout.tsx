import { SidebarNav } from './_components/sidebar-nav';

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="dashboard-shell">
      <SidebarNav />
      <div className="dashboard-shell__content">{children}</div>
    </div>
  );
}
