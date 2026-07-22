import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function DashboardCrmLeadsRedirect() {
  redirect('/workspaces/crm/leads' as Route);
}
