import { redirect } from 'next/navigation';

/** Soft alias — some shell/RSC prefetches target /workspaces/admin/dashboard. */
export default function AdminDashboardAliasPage() {
  redirect('/workspaces/admin');
}
