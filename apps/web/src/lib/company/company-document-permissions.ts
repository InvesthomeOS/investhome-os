import { hasPermission, type CurrentUser } from '@/lib/api/auth';

export function canReadCompanyDocuments(user: CurrentUser | null): boolean {
  return user ? hasPermission(user, 'documents', 'view') : false;
}

export function canCreateCompanyDocuments(user: CurrentUser | null): boolean {
  return user ? hasPermission(user, 'documents', 'create') : false;
}

export function canUpdateCompanyDocuments(user: CurrentUser | null): boolean {
  return user ? hasPermission(user, 'documents', 'update') : false;
}

export function canDownloadCompanyDocuments(user: CurrentUser | null): boolean {
  return user ? hasPermission(user, 'documents', 'download') : false;
}

export function canArchiveCompanyDocuments(user: CurrentUser | null): boolean {
  return user ? hasPermission(user, 'documents', 'archive') : false;
}

export function canApproveCompanyDocuments(user: CurrentUser | null): boolean {
  return user ? hasPermission(user, 'documents', 'approve') : false;
}
