import { redirect } from 'next/navigation';

/** Standalone CRM Search removed — use Dashboard header Ctrl/Cmd+K. */
export default function CrmSavedSearchesPage() {
  redirect('/workspaces/crm/dashboard');
}
