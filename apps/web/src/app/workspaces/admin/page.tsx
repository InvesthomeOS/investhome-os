import { redirect } from 'next/navigation';
import type { Route } from 'next';

/**
 * G1: legacy CRM fixture admin → canonical OS Admin.
 * Deep CRM freeze admin preview remains under /ui-preview/crm/admin.
 */
export default function AdminWorkspacePage() {
  redirect('/dashboard/admin' as Route);
}
