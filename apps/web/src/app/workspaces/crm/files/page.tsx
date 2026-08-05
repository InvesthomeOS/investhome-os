import { redirect } from 'next/navigation';

/**
 * Files module merged into Documents (CRM Belgeler).
 * Preserve bookmark compatibility by redirecting to the unified workspace.
 */
export default function CrmFilesRedirectPage() {
  redirect('/workspaces/crm/documents');
}
