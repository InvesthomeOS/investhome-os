import './investor-theme.css';

import { InvestorShell } from './_components/investor-shell';

export default function InvestorLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <InvestorShell>{children}</InvestorShell>;
}
