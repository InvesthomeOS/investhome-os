import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';

export type CrmPermissionAction =
  | 'read'
  | 'create'
  | 'update'
  | 'delete'
  | 'archive'
  | 'restore'
  | 'export'
  | 'import'
  | 'merge'
  | 'view_companies'
  | 'view_legal'
  | 'view_financial'
  | 'view_compliance'
  | 'edit_ownership'
  | 'transfer_ownership'
  | 'manage_company_contacts'
  | 'bulk_actions'
  | 'view_relationship_confidential'
  | 'view_referral_compensation'
  | 'export_relationship_graph'
  | 'view_activities'
  | 'edit_activities'
  | 'delete_activities'
  | 'view_private_notes'
  | 'manage_tasks'
  | 'manage_meetings'
  | 'manage_followups'
  | 'export_activities'
  | 'view_communications'
  | 'create_communications'
  | 'send_communications'
  | 'schedule_communications'
  | 'edit_communications'
  | 'delete_communications'
  | 'archive_communications'
  | 'export_communications'
  | 'view_private_communications'
  | 'view_restricted_communications'
  | 'manage_templates'
  | 'manage_signatures'
  | 'manage_sequences'
  | 'enroll_sequences'
  | 'view_analytics'
  | 'view_tracking'
  | 'manage_provider_connections'
  | 'manage_settings'
  | 'override_restrictions'
  | 'manage_internal_messages'
  | 'use_global_search'
  | 'advanced_search'
  | 'view_suggestions'
  | 'manage_saved_searches'
  | 'share_saved_searches'
  | 'create_search_alerts'
  | 'search_archived'
  | 'search_restricted'
  | 'search_communication_content'
  | 'search_financial_content'
  | 'search_compliance_content'
  | 'export_search_results'
  | 'view_search_analytics'
  | 'natural_language_search';

export function hasCrmPermission(user: CurrentUser | null, action: CrmPermissionAction): boolean {
  if (!user) return false;
  return hasPermission(user, 'crm', action);
}

export function canReadCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'read');
}

export function canCreateCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'create');
}

export function canUpdateCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'update');
}

export function canDeleteCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'delete');
}

export function canArchiveCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'archive');
}

export function canExportCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'export');
}

export function canImportCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'import');
}

export function canMergeCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'merge');
}

export function canBulkActionsCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'bulk_actions');
}

export function canViewFinancialCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_financial');
}

export function canViewComplianceCrm(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_compliance');
}

export function canViewRelationshipConfidential(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_relationship_confidential');
}

export function canViewReferralCompensation(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_referral_compensation');
}

export function canExportRelationshipGraph(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'export_relationship_graph');
}

export function canViewCrmActivities(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_activities') || canReadCrm(user);
}

export function canViewPrivateNotes(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_private_notes');
}

export function canManageCrmTasks(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'manage_tasks') || canUpdateCrm(user);
}

export function canManageCrmMeetings(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'manage_meetings') || canUpdateCrm(user);
}

export function canManageCrmFollowUps(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'manage_followups') || canUpdateCrm(user);
}

export function canExportCrmActivities(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'export_activities') || canExportCrm(user);
}

export function canUseCrmGlobalSearch(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'use_global_search') || canReadCrm(user);
}

export function canUseCrmAdvancedSearch(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'advanced_search') || canReadCrm(user);
}

export function canManageCrmSavedSearches(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'manage_saved_searches') || canReadCrm(user);
}

export function canExportCrmSearchResults(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'export_search_results') || canExportCrm(user);
}

export function canReadCrmCompanies(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_companies') || canReadCrm(user);
}

export function canViewCommunications(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_communications') || canReadCrm(user);
}

export function canManageCommunicationAccounts(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'manage_provider_connections') || hasCrmPermission(user, 'manage_settings');
}

export function canCreateCommunications(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'create_communications') || canCreateCrm(user);
}

export function canSendCommunications(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'send_communications') || canCreateCommunications(user);
}

export function canManageTemplates(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'manage_templates');
}

export function canViewCommAnalytics(user: CurrentUser | null): boolean {
  return hasCrmPermission(user, 'view_analytics');
}
