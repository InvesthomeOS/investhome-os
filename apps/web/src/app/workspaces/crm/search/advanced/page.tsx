import { redirect } from 'next/navigation';

/** Standalone CRM Search removed — use Dashboard header Ctrl/Cmd+K. */
export default function CrmAdvancedSearchPage() {
  redirect('/workspaces/crm/dashboard');
}
