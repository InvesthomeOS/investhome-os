/** Marketing workspace shared types — aligned with API schemas. */

export type DataSourceStatus =
  | 'connected'
  | 'partially_connected'
  | 'not_connected'
  | 'authentication_required'
  | 'syncing'
  | 'delayed'
  | 'error'
  | 'permission_restricted'
  | 'no_data';

export type DashboardWidgetState =
  | 'loading'
  | 'empty'
  | 'error'
  | 'not_connected'
  | 'permission_restricted'
  | 'no_data'
  | 'ready';

export type MarketingCampaignStatus =
  | 'draft'
  | 'planning'
  | 'pending_approval'
  | 'approved'
  | 'scheduled'
  | 'active'
  | 'paused'
  | 'completed'
  | 'cancelled'
  | 'archived';

export type MarketingCampaignType =
  | 'brand_awareness'
  | 'lead_generation'
  | 'investor_acquisition'
  | 'buyer_acquisition'
  | 'broker_acquisition'
  | 'property_launch'
  | 'project_launch'
  | 'retargeting'
  | 'nurture'
  | 'event_promotion'
  | 'other';

export type MarketingCampaignObjective =
  | 'awareness'
  | 'reach'
  | 'engagement'
  | 'traffic'
  | 'lead_generation'
  | 'conversion'
  | 'retention'
  | 'revenue';

export type MarketingCampaignPrimaryChannel =
  | 'meta'
  | 'google'
  | 'seo'
  | 'email'
  | 'sms'
  | 'whatsapp'
  | 'content'
  | 'youtube'
  | 'linkedin'
  | 'referral'
  | 'event'
  | 'other';

export type MarketingMetricValue = {
  value: number | string | null;
  available: boolean;
  reason: string | null;
};

export type MarketingWorkspaceOverview = {
  total_campaigns: MarketingMetricValue;
  active_campaigns: MarketingMetricValue;
  budget: MarketingMetricValue;
  spend: MarketingMetricValue;
  estimated_leads: MarketingMetricValue;
  actual_leads: MarketingMetricValue;
  estimated_roi: MarketingMetricValue;
  top_performing: MarketingMetricValue;
  upcoming: MarketingMetricValue;
  qualified_leads?: MarketingMetricValue | null;
  converted_leads?: MarketingMetricValue | null;
  avg_cpl?: MarketingMetricValue | null;
  avg_conversion_rate?: MarketingMetricValue | null;
  campaigns_requiring_attention?: MarketingMetricValue | null;
  currency: string | null;
  upcoming_campaigns: MarketingCampaignSummary[];
};

export type MarketingCampaignSummary = {
  id: string;
  name: string;
  code: string | null;
  objective: MarketingCampaignObjective;
  campaign_type: MarketingCampaignType;
  status: MarketingCampaignStatus;
  priority: string;
  owner_user_id: string | null;
  company_id?: string | null;
  target_project_id?: string | null;
  lead_source_id?: string | null;
  primary_channel?: MarketingCampaignPrimaryChannel | null;
  start_date: string | null;
  end_date: string | null;
  budget_amount: string | null;
  budget_currency: string | null;
  spent_amount?: string | null;
  actual_leads?: number | null;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

export type MarketingCampaignDetail = MarketingCampaignSummary & {
  description: string | null;
  team_id: string | null;
  project_ids: string[] | null;
  property_ids: string[] | null;
  audience_ids: string[] | null;
  segment_ids: string[] | null;
  channel_ids: string[] | null;
  timezone: string | null;
  targets_json: Record<string, unknown> | null;
  notes?: string | null;
  metadata_json?: Record<string, unknown> | null;
  archived_at: string | null;
  remaining_budget?: string | null;
};

export type MarketingDashboardWidget = {
  key: string;
  state: DashboardWidgetState;
  title_key: string;
  data: Record<string, unknown> | unknown[] | null;
};

export type MarketingProviderStatus = {
  channel_id: string;
  channel_name: string;
  category: string;
  provider: string | null;
  connection_status: DataSourceStatus;
  last_sync_at: string | null;
};

export type MarketingAlertSummary = {
  id: string;
  title: string;
  message: string | null;
  category: string;
  severity: string;
  is_resolved: boolean;
  created_at: string;
};

export type MarketingRecommendationSummary = {
  id: string;
  title: string;
  description: string | null;
  recommendation_type: string;
  rationale: string | null;
  confidence_level: string | null;
  status: string;
  created_at: string;
};

export type MarketingDashboardData = {
  widgets: MarketingDashboardWidget[];
  active_campaigns: MarketingCampaignSummary[];
  alerts: MarketingAlertSummary[];
  recommendations: MarketingRecommendationSummary[];
  provider_statuses: MarketingProviderStatus[];
  campaign_count: number;
  audience_count: number;
  lead_context_count: number;
  workspace_overview?: MarketingWorkspaceOverview | null;
};

export type MarketingNavItem = {
  href: string;
  labelKey: string;
  permission?: string;
};

export type MarketingNavGroup = {
  key: string;
  labelKey: string;
  items: MarketingNavItem[];
};

export type MarketingNavigationData = {
  groups: MarketingNavGroup[];
};

export type MarketingQuickAction = {
  key: string;
  label_key: string;
  href: string;
  permission: string;
};

export type MarketingQuickActionsData = {
  actions: MarketingQuickAction[];
};

export type MarketingCampaignListResponse = {
  items: MarketingCampaignSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type UtmParams = {
  utm_source?: string | null;
  utm_medium?: string | null;
  utm_campaign?: string | null;
  utm_term?: string | null;
  utm_content?: string | null;
};

/** Single nav definition — grouped, permission-filtered on client and server. */
/** Primary marketing nav — Overview, Campaigns, Assets, Reports, AI Assistant, Calendar, Settings (+ existing modules). */
export const MARKETING_NAV_GROUPS: MarketingNavGroup[] = [
  {
    key: 'overview',
    labelKey: 'nav.groups.overview',
    items: [
      { href: '/workspaces/marketing/dashboard', labelKey: 'nav.dashboard', permission: 'view_dashboard' },
      { href: '/workspaces/marketing/campaigns', labelKey: 'nav.campaigns', permission: 'manage_campaigns' },
      { href: '/workspaces/marketing/assets', labelKey: 'nav.assets', permission: 'manage_assets' },
      { href: '/workspaces/marketing/reports', labelKey: 'nav.reports', permission: 'export_analytics' },
      { href: '/workspaces/marketing/ai/assistant', labelKey: 'nav.aiAssistant', permission: 'view_ai' },
      { href: '/workspaces/marketing/calendar', labelKey: 'nav.calendar', permission: 'view' },
      { href: '/workspaces/marketing/settings', labelKey: 'nav.settings', permission: 'manage_settings' },
    ],
  },
  {
    key: 'demand_generation',
    labelKey: 'nav.groups.demandGeneration',
    items: [
      { href: '/workspaces/marketing/audiences', labelKey: 'nav.audiences', permission: 'manage_audiences' },
      { href: '/workspaces/marketing/segments', labelKey: 'nav.segments', permission: 'manage_segments' },
      { href: '/workspaces/marketing/leads', labelKey: 'nav.leads', permission: 'view_leads' },
      { href: '/workspaces/marketing/sources', labelKey: 'nav.sources', permission: 'manage_campaigns' },
      { href: '/workspaces/marketing/landing-pages', labelKey: 'nav.landingPages', permission: 'manage_campaigns' },
      { href: '/workspaces/marketing/forms', labelKey: 'nav.forms', permission: 'manage_campaigns' },
    ],
  },
  {
    key: 'content',
    labelKey: 'nav.groups.content',
    items: [
      { href: '/workspaces/marketing/content', labelKey: 'nav.contentStudio', permission: 'publish_content' },
      { href: '/workspaces/marketing/social', labelKey: 'nav.social', permission: 'publish_content' },
      { href: '/workspaces/marketing/email', labelKey: 'nav.email', permission: 'send_email' },
      { href: '/workspaces/marketing/whatsapp', labelKey: 'nav.whatsapp', permission: 'send_whatsapp' },
      { href: '/workspaces/marketing/sms', labelKey: 'nav.sms', permission: 'send_sms' },
      { href: '/workspaces/marketing/templates', labelKey: 'nav.templates', permission: 'publish_content' },
    ],
  },
  {
    key: 'paid_media',
    labelKey: 'nav.groups.paidMedia',
    items: [
      { href: '/workspaces/marketing/advertising', labelKey: 'nav.advertising', permission: 'manage_advertising' },
      { href: '/workspaces/marketing/budgets', labelKey: 'nav.budgets', permission: 'manage_budgets' },
      { href: '/workspaces/marketing/attribution', labelKey: 'nav.attribution', permission: 'view_attribution' },
      { href: '/workspaces/marketing/analytics', labelKey: 'nav.analytics', permission: 'export_analytics' },
      { href: '/workspaces/marketing/forecasting', labelKey: 'nav.forecasting', permission: 'view_ai' },
      { href: '/workspaces/marketing/ai', labelKey: 'nav.ai', permission: 'view_ai' },
    ],
  },
  {
    key: 'operations',
    labelKey: 'nav.groups.operations',
    items: [
      { href: '/workspaces/marketing/events', labelKey: 'nav.events', permission: 'manage_events' },
      { href: '/workspaces/marketing/brand', labelKey: 'nav.brand', permission: 'manage_brand' },
      { href: '/workspaces/marketing/automations', labelKey: 'nav.automations', permission: 'manage_automations' },
      { href: '/workspaces/marketing/approvals', labelKey: 'nav.approvals', permission: 'approve_content' },
      { href: '/workspaces/marketing/vendors', labelKey: 'nav.vendors', permission: 'manage_settings' },
    ],
  },
];

export const MARKETING_MODULE_KEYS = [
  'campaigns',
  'audiences',
  'segments',
  'leads',
  'sources',
  'landingPages',
  'forms',
  'contentStudio',
  'social',
  'email',
  'whatsapp',
  'sms',
  'advertising',
  'events',
  'assets',
  'brand',
  'templates',
  'calendar',
  'attribution',
  'analytics',
  'automations',
  'approvals',
  'budgets',
  'vendors',
  'reports',
  'settings',
] as const;

export type MarketingModuleKey = (typeof MARKETING_MODULE_KEYS)[number];

export const DEFAULT_CAMPAIGN_SAVED_VIEWS = [
  { key: 'all', filters: {} },
  { key: 'myCampaigns', filters: { my_campaigns: true } },
  { key: 'active', filters: { status: 'active' } },
  { key: 'pendingApproval', filters: { status: 'pending_approval' } },
  { key: 'draft', filters: { status: 'draft' } },
  { key: 'missingBudget', filters: { missing_budget: true } },
  { key: 'missingTracking', filters: { missing_tracking: true } },
] as const;

export const CAMPAIGN_WIZARD_STEPS = [
  'basics',
  'objective',
  'projects',
  'audience',
  'channels',
  'schedule',
  'budget',
  'targets',
  'ownership',
  'tracking',
  'approvals',
  'review',
] as const;

export type CampaignWizardStep = (typeof CAMPAIGN_WIZARD_STEPS)[number];

export const CAMPAIGN_DETAIL_TABS = [
  'overview',
  'planning',
  'audience',
  'channels',
  'content',
  'assets',
  'landing-pages',
  'forms',
  'budget',
  'leads',
  'attribution',
  'analytics',
  'approvals',
  'activity',
  'settings',
] as const;

export type CampaignDetailTab = (typeof CAMPAIGN_DETAIL_TABS)[number];

export const CONTENT_WIZARD_STEPS = [
  'basics',
  'brief',
  'objective',
  'audience',
  'projects',
  'channels',
  'format',
  'assets',
  'brand',
  'legal',
  'approvals',
  'schedule',
  'variants',
  'review',
] as const;

export type ContentWizardStep = (typeof CONTENT_WIZARD_STEPS)[number];

export const CONTENT_DETAIL_TABS = [
  'overview',
  'brief',
  'editor',
  'versions',
  'channels',
  'campaigns',
  'assets',
  'approvals',
  'activity',
  'settings',
] as const;

export type ContentDetailTab = (typeof CONTENT_DETAIL_TABS)[number];

export const AUDIENCE_WIZARD_STEPS = [
  'basics',
  'mode',
  'contacts',
  'segments',
  'consent',
  'channels',
  'geo',
  'exclusions',
  'refresh',
  'review',
  'confirm',
] as const;

export type AudienceWizardStep = (typeof AUDIENCE_WIZARD_STEPS)[number];

export type AudienceWizardDraft = {
  name: string;
  description: string | null;
  mode: string;
  audience_type: string;
  language: string | null;
  contact_ids: string[];
  segment_ids: string[];
  consent_requirements_json: Record<string, unknown> | null;
  channel_ids: string[];
  geo_json: Record<string, unknown> | null;
  exclusion_refs_json: Record<string, unknown> | null;
  refresh_policy_json: Record<string, unknown> | null;
};

export const EMAIL_CAMPAIGN_WIZARD_STEPS = [
  'basics',
  'objective',
  'audience',
  'sender',
  'subject',
  'preview',
  'content',
  'template',
  'scheduling',
  'tracking',
  'consent',
  'personalisation',
  'review',
  'confirm',
] as const;

export type EmailCampaignWizardStep = (typeof EMAIL_CAMPAIGN_WIZARD_STEPS)[number];

export type EmailCampaignWizardDraft = {
  name: string;
  subject: string | null;
  preview_text: string | null;
  audience_id: string | null;
  marketing_campaign_id: string | null;
  content_id: string | null;
  template_id: string | null;
  sender_profile_id: string | null;
  scheduled_at: string | null;
  unsubscribe_required: boolean;
  unsubscribe_link_present: boolean;
  wizard_state_json: Record<string, unknown> | null;
};
