import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function CrmRootPage() {
  redirect('/workspaces/crm/dashboard' as Route);
}
