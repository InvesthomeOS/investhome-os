import { redirect } from 'next/navigation';
import type { Route } from 'next';

/** Alias for brief path `/dashboard/crm` → real CRM workspace. */
export default function DashboardCrmRedirect() {
  redirect('/workspaces/crm/dashboard' as Route);
}
