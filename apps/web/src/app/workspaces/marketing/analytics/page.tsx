import { redirect } from 'next/navigation';
import type { Route } from 'next';

/** Sidebar "Analytics" entry — routes to the analytics command center. */
export default function MarketingAnalyticsPage() {
  redirect('/workspaces/marketing/dashboard/executive' as Route);
}
