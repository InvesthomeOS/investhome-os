export const AI_VIEWS = [
  'command_center',
  'morning_brief',
  'copilot',
  'action_center',
  'crm_intel',
  'investor_intel',
  'project_intel',
  'finance_intel',
  'marketing_intel',
  'document_intel',
  'meeting_intel',
  'forecasts',
  'risk_center',
  'ai_search',
  'prompt_library',
  'activity_log',
  'settings',
  'provider_status',
] as const;

export type AiViewId = (typeof AI_VIEWS)[number];

export function parseView(raw: string | null): AiViewId {
  if (raw && (AI_VIEWS as readonly string[]).includes(raw)) {
    return raw as AiViewId;
  }
  return 'command_center';
}

/** LIVE | PARTIAL | DEMO | BLOCKED | NOT_CONFIGURED */
export type DataKind = 'live' | 'partial' | 'demo' | 'blocked' | 'not_configured';

export const VIEW_DATA_KIND: Record<AiViewId, DataKind> = {
  command_center: 'partial',
  morning_brief: 'partial',
  copilot: 'partial',
  action_center: 'partial',
  crm_intel: 'partial',
  investor_intel: 'partial',
  project_intel: 'partial',
  finance_intel: 'partial',
  marketing_intel: 'partial',
  document_intel: 'partial',
  meeting_intel: 'demo',
  forecasts: 'partial',
  risk_center: 'partial',
  ai_search: 'partial',
  prompt_library: 'live',
  activity_log: 'partial',
  settings: 'partial',
  provider_status: 'partial',
};

export const MORNING_BRIEF_THEMES = [
  'changed',
  'decisions',
  'overdue',
  'atRisk',
  'moneyIn',
  'moneyOut',
  'investorFollowup',
  'projectDelay',
  'campaigns',
  'documents',
  'meetings',
  'priorities',
] as const;

export type MorningBriefTheme = (typeof MORNING_BRIEF_THEMES)[number];

export const SENSITIVE_ACTIONS = [
  'send_email',
  'change_investor_stage',
  'change_opportunity_stage',
  'approve_payment',
  'release_payment',
  'create_legal_document',
  'modify_contract',
  'modify_financial_record',
  'delete_record',
  'change_project_dates',
  'change_budget',
  'publish_content',
  'pause_campaign',
  'initiate_automation',
] as const;

export type SensitiveAction = (typeof SENSITIVE_ACTIONS)[number];

export const PROVIDER_STATES = [
  'operational',
  'degraded',
  'unavailable',
  'not_configured',
  'rate_limited',
] as const;

export type ProviderState = (typeof PROVIDER_STATES)[number];
