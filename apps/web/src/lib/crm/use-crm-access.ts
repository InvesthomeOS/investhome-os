'use client';

import { useAuth } from '@/lib/auth/auth-context';
import {
  canCreateCrm,
  canImportCrm,
  canManageCrmTasks,
  canReadCrm,
  canReadCrmCompanies,
  canViewCommunications,
  type CrmPermissionAction,
  hasCrmPermission,
} from '@/lib/crm/crm-permissions';

/**
 * Auth-aware CRM access helpers.
 * Callers MUST wait for `authLoading` before rendering access-denied UI.
 */
export function useCrmAccess() {
  const { user, loading: authLoading } = useAuth();

  return {
    user,
    authLoading,
    canRead: canReadCrm(user),
    canCreate: canCreateCrm(user),
    canImport: canImportCrm(user),
    canManageTasks: canManageCrmTasks(user),
    canReadCompanies: canReadCrmCompanies(user),
    canViewCommunications: canViewCommunications(user),
    has: (action: CrmPermissionAction) => hasCrmPermission(user, action),
  };
}
