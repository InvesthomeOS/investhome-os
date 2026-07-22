import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function DashboardCrmContactsRedirect() {
  redirect('/workspaces/crm/contacts' as Route);
}
