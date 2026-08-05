import { redirect } from 'next/navigation';
import type { Route } from 'next';

/** G1: /workspaces/marketing root → canonical OS Marketing. */
export default function MarketingRootPage() {
  redirect('/dashboard/marketing' as Route);
}
