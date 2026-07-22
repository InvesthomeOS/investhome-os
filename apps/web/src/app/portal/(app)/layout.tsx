import { PortalShell } from '../_components/portal-shell';

export default function PortalAppLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <PortalShell>{children}</PortalShell>;
}
