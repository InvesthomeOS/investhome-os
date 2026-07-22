import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';

export type MarketingPermissionAction =
  | 'view'
  | 'create'
  | 'update'
  | 'delete'
  | 'archive'
  | 'restore'
  | 'export'
  | 'view_dashboard'
  | 'manage_campaigns'
  | 'activate_campaign'
  | 'pause_campaign'
  | 'manage_audiences'
  | 'manage_segments'
  | 'refresh_segments'
  | 'manage_audience_members'
  | 'view_audience_consent'
  | 'manage_segment_rules'
  | 'view_leads'
  | 'view_attribution'
  | 'view_scores'
  | 'hand_to_sales'
  | 'verify'
  | 'manage_suppression'
  | 'manage_source_mapping'
  | 'manage_source_normalization'
  | 'publish_content'
  | 'approve_content'
  | 'send_email'
  | 'send_whatsapp'
  | 'send_sms'
  | 'manage_provider_connections'
  | 'manage_budgets'
  | 'approve_budget'
  | 'view_spend'
  | 'manage_advertising'
  | 'manage_events'
  | 'manage_automations'
  | 'export_analytics'
  | 'view_ai'
  | 'query_copilot'
  | 'manage_ai_settings'
  | 'use_ai'
  | 'save_ai'
  | 'export_ai'
  | 'manage_settings'
  | 'manage_assets'
  | 'manage_brand'
  | 'manage_forms'
  | 'manage_landing_pages';

export function hasMarketingPermission(
  user: CurrentUser | null,
  action: MarketingPermissionAction,
): boolean {
  if (!user) return false;
  return hasPermission(user, 'marketing', action);
}

export function canReadMarketing(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'view') || hasMarketingPermission(user, 'view_dashboard');
}

export const canViewMarketing = canReadMarketing;

export function canViewMarketingDashboard(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'view_dashboard') || canReadMarketing(user);
}

export function canManageCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'manage_campaigns');
}

export function canCreateCampaigns(user: CurrentUser | null): boolean {
  return canManageCampaigns(user) || hasMarketingPermission(user, 'create');
}

export function canActivateCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'activate_campaign');
}

export function canPauseCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'pause_campaign');
}

export function canArchiveCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'archive');
}

export function canDeleteCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'delete');
}

export function canExportCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'export');
}

export function canApproveCampaigns(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'approve_content');
}

export function canViewCampaignBudget(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'manage_budgets') || hasMarketingPermission(user, 'view_spend');
}

export function canEditCampaignBudget(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'manage_budgets');
}

export function canViewCampaignLeads(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'view_leads');
}

export function canViewCampaignAnalytics(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'export_analytics');
}

export function canViewCampaignAttribution(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'view_attribution');
}

export function canManageBrand(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'manage_brand');
}

export function canManageAssets(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'manage_assets');
}

export function canPublishContent(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'publish_content');
}

export function canApproveContent(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'approve_content');
}

export function canPublishSocial(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'publish_content');
}

export function canSendEmail(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'send_email');
}

export function canSendWhatsapp(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'send_whatsapp');
}

export function canSendSms(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'send_sms');
}

export function canViewMarketingAI(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'view_ai') || hasMarketingPermission(user, 'view_dashboard');
}

export function canQueryCopilot(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'query_copilot') || hasMarketingPermission(user, 'view_ai');
}

export function canManageAISettings(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'manage_ai_settings');
}

export function canUseMarketingAI(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'use_ai');
}

export function canSaveMarketingAI(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'save_ai');
}

export function canExportMarketingAI(user: CurrentUser | null): boolean {
  return hasMarketingPermission(user, 'export_ai') || hasMarketingPermission(user, 'export');
}

export function filterNavByPermission(
  user: CurrentUser | null,
  groups: { key: string; labelKey: string; items: { href: string; labelKey: string; permission?: string }[] }[],
) {
  return groups
    .map((group) => ({
      ...group,
      items: group.items.filter(
        (item) => !item.permission || hasMarketingPermission(user, item.permission as MarketingPermissionAction),
      ),
    }))
    .filter((group) => group.items.length > 0);
}
