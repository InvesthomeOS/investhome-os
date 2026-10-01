import { redirect } from 'next/navigation';
import type { Route } from 'next';

export default function CrmPeoplePage() {
  redirect('/workspaces/crm/contacts' as Route);
}
