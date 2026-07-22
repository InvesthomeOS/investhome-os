import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function DashboardCrmCompaniesRedirect() {
  redirect('/workspaces/crm/companies' as Route);
}
