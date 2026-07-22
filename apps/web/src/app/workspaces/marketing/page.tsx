import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function MarketingRootPage() {
  redirect('/workspaces/marketing/dashboard' as Route);
}
