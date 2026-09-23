/** CRM workspace shared types — aligned with API schemas. */

export type CrmContactType =
  | 'investor'
  | 'prospect'
  | 'buyer'
  | 'broker'
  | 'realtor'
  | 'partner'
  | 'vendor'
  | 'contractor'
  | 'attorney'
  | 'lender'
  | 'property_manager'
  | 'architect'
  | 'consultant'
  | 'media_contact'
  | 'government_contact'
  | 'internal_team';

export type CrmRecordKind = 'person' | 'organization';

export type CrmContactStatus = 'active' | 'inactive' | 'prospect' | 'archived';

export type CrmLifecycleStage =
  | 'new'
  | 'engaged'
  | 'qualified'
  | 'active_relationship'
  | 'dormant'
  | 'churned';

export type CrmRelationshipStatus =
  | 'unknown'
  | 'cold'
  | 'warm'
  | 'hot'
  | 'active'
  | 'at_risk'
  | 'lost';

export type CrmRelationshipStrength = 'weak' | 'moderate' | 'strong' | 'strategic';

export type CrmContactPriority = 'low' | 'normal' | 'high' | 'urgent';

export type CrmContactSummary = {
  id: string;
  contact_type: CrmContactType;
  contact_types: CrmContactType[];
  record_kind: CrmRecordKind;
  display_name: string;
  organization_name: string | null;
  primary_email: string | null;
  primary_phone: string | null;
  source: string | null;
  status: CrmContactStatus;
  lifecycle_stage: CrmLifecycleStage;
  relationship_status: CrmRelationshipStatus;
  relationship_strength: CrmRelationshipStrength;
  priority: CrmContactPriority;
  tags: string[] | null;
  tag_items?: Array<{ id: string; name: string; status?: string }>;
  is_favorite: boolean;
  is_pinned: boolean;
  owner_user_id: string | null;
  owner_name: string | null;
  company_id: string | null;
  company_name: string | null;
  lead_id: string | null;
  investor_id: string | null;
  last_contact_at: string | null;
  next_follow_up_at: string | null;
  relationship_score: number;
  engagement_score: number;
  junk_reason?: string | null;
  junked_at?: string | null;
  review_required?: boolean;
  is_agent?: boolean;
  has_agreements?: boolean;
  agreement_count?: number;
  verified_amount_totals?: Array<{ currency: string | null; total: string; label: string }>;
  agreement_projects?: string[];
  bitrix_original_stage: string | null;
  bitrix_historical_junk: boolean;
  bitrix_source_channel?: string | null;
  bitrix_responsible?: string | null;
  secondary_emails?: string[] | null;
  secondary_phones?: string[] | null;
  whatsapp?: string | null;
  job_title?: string | null;
  city?: string | null;
  address_line1?: string | null;
  notes?: string | null;
  updated_at: string;
  created_at: string;
};

export type CrmPurchaseParticipant = {
  contact_id: string;
  display_name: string;
  role: string;
  ownership_pct: string | null;
  is_primary: boolean;
  source: string | null;
};

export type CrmPurchaseSummary = {
  agreement_id: string;
  bitrix_deal_id: string | null;
  project_group: string;
  project_label: string;
  unit_number: string | null;
  amount: string | null;
  currency: string | null;
  amount_label: string | null;
  stage: string | null;
  begin_date: string | null;
  close_date: string | null;
  owners_label: string | null;
  participants: CrmPurchaseParticipant[];
  opens_purchase_card: boolean;
  status?: string | null;
  hemen_kira?: boolean;
  is_historical_unit_change?: boolean;
  unit_change_status?: string | null;
  original_unit?: string | null;
  final_unit?: string | null;
  unit_history?: Array<{
    agreement_id: string;
    unit_number: string;
    is_current: boolean;
    is_historical_unit_change?: boolean;
    contact_id?: string | null;
  }>;
};

export type CrmContactDetail = CrmContactSummary & {
  first_name: string | null;
  last_name: string | null;
  job_title: string | null;
  department: string | null;
  secondary_emails: string[] | null;
  secondary_phones: string[] | null;
  linkedin_url: string | null;
  whatsapp: string | null;
  website: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state_province: string | null;
  postal_code: string | null;
  country: string | null;
  referred_by_contact_id: string | null;
  notes: string | null;
  communication_prefs: Record<string, unknown> | null;
  compliance_data: Record<string, unknown> | null;
  investment_profile: Record<string, unknown> | null;
  buyer_profile: Record<string, unknown> | null;
  broker_profile: Record<string, unknown> | null;
  vendor_profile: Record<string, unknown> | null;
  bitrix_history: {
    external_ids: string[];
    source_files: string[];
    source_roles: string[];
    historical_junk: boolean;
    original_asama: string | null;
    mapped_sales_stage: string | null;
    conflict_fields: string[];
    warning_flags: string[];
    junk_reason?: string | null;
    review_required?: boolean;
  } | null;
  amount_and_currency_label?: string | null;
  amount_and_currency_field_id?: string | null;
  amount_and_currency_amount?: string | null;
  amount_and_currency_currency?: string | null;
  project_card_pilot?: {
    enabled: boolean;
    canonical_contact_id: string | null;
    selected_project: string;
    available_projects: Array<{ id: string; label: string }>;
    history_counts: Record<string, number>;
    unclassified_history_count: number;
    tutar_by_project: Record<string, string>;
  } | null;
  purchases?: CrmPurchaseSummary[];
  profile_fields?: Array<{ label: string; value: string }>;
  crm_activities: Array<{
    id: string;
    activity_type: string;
    activity_category: string;
    title: string;
    description: string | null;
    status: string;
    imported_historical_comment: boolean;
    due_date?: string | null;
    assigned_user_id?: string | null;
    task_status?: string | null;
    created_at: string;
  }>;
  crm_agreements: Array<{
    id: string;
    project_group: string;
    project_label: string;
    status: string;
    agreement_date: string | null;
    unit_number?: string | null;
    investment_amount?: string | null;
    payment_amount?: string | null;
    deposit?: string | null;
    purchase_price?: string | null;
    amount_and_currency_label?: string | null;
    amount_and_currency_field_id?: string | null;
    amount_and_currency_amount?: string | null;
    amount_and_currency_currency?: string | null;
    email?: string | null;
    phone?: string | null;
    review_required?: boolean;
    relationship?: string;
  }>;
  agent: {
    is_agent: boolean;
    status: string;
    contact_types: CrmContactType[];
    brokerage_name: string | null;
    specialization: string | null;
  } | null;
};

export type CrmActivitySummary = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  description_key: string;
  actor_name: string | null;
  created_at: string;
};

export type CrmTaskSummary = {
  id: string;
  title: string;
  status: string;
  due_at: string | null;
  priority: string | null;
};

export type CrmMeetingSummary = {
  id: string;
  title: string;
  start_at: string | null;
  status: string | null;
};

export type CrmRelationshipAlert = {
  contact_id: string;
  display_name: string;
  alert_type: string;
  message_key: string;
  severity: string;
};

export type CrmPinnedCompanySummary = {
  contact_id: string;
  display_name: string;
  organization_name: string | null;
  contact_type: CrmContactType;
};

export type CrmCommunicationSummary = {
  total_contacts: number;
  contacts_with_email: number;
  contacts_with_phone: number;
  favorites_count: number;
  recent_interactions_count: number;
};

export type CrmDashboardCount = {
  key: string;
  label: string;
  count: number;
  href?: string | null;
};

export type CrmDashboardKpis = {
  current_purchases: number;
  investors: number;
  active_tasks: number;
  open_leads: number;
  documents_review: number;
  matches_pending: number;
};

export type CrmDashboardPurchaseScope = {
  current: number;
  historical: number;
  total: number;
};

export type CrmDashboardFeedItem = {
  id: string;
  title: string;
  meta?: string | null;
  href: string;
  occurred_at?: string | null;
  kind: string;
};

export type CrmDashboardData = {
  recent_contacts: CrmContactSummary[];
  recent_activities: CrmActivitySummary[];
  upcoming_tasks: CrmTaskSummary[];
  todays_meetings: CrmMeetingSummary[];
  recently_updated: CrmContactSummary[];
  relationship_alerts: CrmRelationshipAlert[];
  favorite_contacts: CrmContactSummary[];
  pinned_companies: CrmPinnedCompanySummary[];
  communication_summary: CrmCommunicationSummary;
  kpis: CrmDashboardKpis;
  purchase_scope: CrmDashboardPurchaseScope;
  charts: {
    purchases_by_project: CrmDashboardCount[];
    purchases_by_month: CrmDashboardCount[];
    task_status: CrmDashboardCount[];
    communication_channels: CrmDashboardCount[];
    lead_pipeline: CrmDashboardCount[];
    document_status: CrmDashboardCount[];
  };
  panels: {
    recent_activities: CrmDashboardFeedItem[];
    upcoming_tasks: CrmDashboardFeedItem[];
    recent_documents: CrmDashboardFeedItem[];
    review_queue: CrmDashboardFeedItem[];
    recent_leads: CrmDashboardFeedItem[];
  };
};

export type CrmContactListResponse = {
  items: CrmContactSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
};

export type CrmNavItem = {
  href: string;
  labelKey: string;
};

export const CRM_NAV_ITEMS: CrmNavItem[] = [
  { href: '/workspaces/crm/dashboard', labelKey: 'nav.dashboard' },
  { href: '/workspaces/crm/leads', labelKey: 'nav.leads' },
  { href: '/workspaces/crm/pipeline', labelKey: 'nav.pipeline' },
  { href: '/workspaces/crm/matches', labelKey: 'nav.matches' },
  { href: '/workspaces/crm/contacts', labelKey: 'nav.contacts' },
  { href: '/workspaces/crm/junk', labelKey: 'nav.junk' },
  { href: '/workspaces/crm/agents', labelKey: 'nav.agents' },
  { href: '/workspaces/crm/agreements', labelKey: 'nav.agreements' },
  { href: '/workspaces/crm/companies', labelKey: 'nav.companies' },
  { href: '/workspaces/crm/investors', labelKey: 'nav.investors' },
  { href: '/workspaces/crm/relationships', labelKey: 'nav.relationships' },
  { href: '/workspaces/crm/timeline', labelKey: 'nav.timeline' },
  { href: '/workspaces/crm/activities', labelKey: 'nav.activities' },
  { href: '/workspaces/crm/tasks', labelKey: 'nav.tasks' },
  { href: '/workspaces/crm/calendar', labelKey: 'nav.calendar' },
  { href: '/workspaces/crm/notes', labelKey: 'nav.notes' },
  { href: '/workspaces/crm/tags', labelKey: 'nav.tags' },
  { href: '/workspaces/crm/communication', labelKey: 'nav.communication' },
  { href: '/workspaces/crm/documents', labelKey: 'nav.documents' },
  { href: '/workspaces/crm/reports', labelKey: 'nav.reports' },
  { href: '/workspaces/crm/settings', labelKey: 'nav.settings' },
];

export const CRM_CONTACT_TYPES: CrmContactType[] = [
  'investor',
  'prospect',
  'buyer',
  'broker',
  'realtor',
  'partner',
  'vendor',
  'contractor',
  'attorney',
  'lender',
  'property_manager',
  'architect',
  'consultant',
  'media_contact',
  'government_contact',
  'internal_team',
];

export const CRM_LIFECYCLE_STAGES: CrmLifecycleStage[] = [
  'new',
  'engaged',
  'qualified',
  'active_relationship',
  'dormant',
  'churned',
];

export const CRM_PRIORITIES: CrmContactPriority[] = ['low', 'normal', 'high', 'urgent'];

export const DEFAULT_SAVED_VIEWS = [
  { key: 'all', filters: {} },
  { key: 'investors', filters: { contact_type: 'investor' } },
  { key: 'prospects', filters: { contact_type: 'prospect' } },
  { key: 'followUpDue', filters: { sort_by: 'next_follow_up_at', sort_dir: 'asc' } },
  { key: 'highPriority', filters: { priority: 'high' } },
  { key: 'stale', filters: { lifecycle_stage: 'dormant' } },
] as const;

export type CrmCompanyType =
  | 'investment_company'
  | 'buyer_entity'
  | 'brokerage'
  | 'law_firm'
  | 'bank'
  | 'lender'
  | 'property_management'
  | 'construction'
  | 'contractor'
  | 'architecture'
  | 'accounting'
  | 'consulting'
  | 'insurance'
  | 'media'
  | 'government'
  | 'vendor'
  | 'partner'
  | 'internal_entity'
  | 'other';

export type CrmCompanyStatus = 'active' | 'inactive' | 'prospect' | 'archived';

export type CrmCompanyListItem = {
  id: string;
  display_name: string;
  legal_name: string | null;
  company_type: CrmCompanyType;
  company_types: string[] | null;
  entity_type: string | null;
  status: CrmCompanyStatus;
  lifecycle_stage: string;
  primary_email: string | null;
  primary_phone: string | null;
  domain: string | null;
  industry: string | null;
  relationship_status: string;
  relationship_strength: string;
  owner_user_id: string | null;
  owner_name?: string | null;
  parent_company_id: string | null;
  tags: string[] | null;
  is_favorite: boolean;
  is_pinned: boolean;
  contact_count: number;
  city?: string | null;
  country?: string | null;
  related_people?: Array<{ id: string; display_name: string; contact_type?: string | null; is_broker?: boolean }>;
  open_relationship_count?: number;
  related_agreement_count?: number;
  last_activity_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
};

export type CrmCompanyContactLink = {
  id: string;
  contact_id: string;
  role: string;
  job_title: string | null;
  department: string | null;
  relationship_type: string | null;
  ownership_percent: number | null;
  signing_authority: boolean;
  is_primary: boolean;
  status: string;
  contact_display_name: string | null;
};

export type CrmCompanyDetail = CrmCompanyListItem & {
  trade_name: string | null;
  registration_number: string | null;
  tax_id: string | null;
  ein: string | null;
  website: string | null;
  linkedin_url: string | null;
  employee_count: number | null;
  annual_revenue: number | null;
  description: string | null;
  relationship_score: number;
  source: string | null;
  notes: string | null;
  contacts: CrmCompanyContactLink[];
  relationships: Array<{
    id: string;
    target_company_id: string;
    relationship_type: string;
    target_display_name: string | null;
  }>;
  financial_profile: Record<string, unknown> | null;
  investment_profile: Record<string, unknown> | null;
  brokerage_profile: Record<string, unknown> | null;
  lender_profile: Record<string, unknown> | null;
  vendor_profile: Record<string, unknown> | null;
  law_firm_profile: Record<string, unknown> | null;
  property_management_profile: Record<string, unknown> | null;
  compliance_data: Record<string, unknown> | null;
  addresses?: Array<{
    id: string;
    city: string | null;
    country: string | null;
    address_line1: string | null;
    is_primary: boolean;
  }>;
  related_agreements?: Array<{
    id: string;
    project_group: string;
    unit_number: string | null;
    investment_amount: string | null;
    contact_id: string;
    contact_display_name: string | null;
  }>;
  last_contact_at?: string | null;
  incorporation_country?: string | null;
};

export type CrmCompanyListResponse = {
  items: CrmCompanyListItem[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export type CrmCompanyHierarchyNode = {
  id: string;
  display_name: string;
  company_type: string;
  status: string;
  parent_company_id: string | null;
  children: CrmCompanyHierarchyNode[];
};

export type CrmCompanyHierarchyResponse = {
  roots: CrmCompanyHierarchyNode[];
};

export type CrmCompanyImportResult = {
  imported: number;
  skipped: number;
  errors: string[];
};

export type CrmCompanySavedView = {
  id: string;
  name: string;
  filters: Record<string, unknown> | null;
  columns: string[] | null;
  sort_by: string | null;
  sort_order: string | null;
  is_default: boolean;
};

export type CrmCompanyTimelineResponse = {
  items: Array<{
    id: string;
    action: string;
    description_key: string;
    actor_name: string | null;
    created_at: string;
  }>;
  total: number;
};

export const CRM_COMPANY_TYPES: CrmCompanyType[] = [
  'investment_company',
  'buyer_entity',
  'brokerage',
  'law_firm',
  'bank',
  'lender',
  'property_management',
  'construction',
  'contractor',
  'architecture',
  'accounting',
  'consulting',
  'insurance',
  'media',
  'government',
  'vendor',
  'partner',
  'internal_entity',
  'other',
];

export const DEFAULT_COMPANY_SAVED_VIEWS = [
  { key: 'all', filters: {} },
  { key: 'investors', filters: { company_type: 'investment_company' } },
  { key: 'brokerages', filters: { company_type: 'brokerage' } },
  { key: 'lenders', filters: { company_type: 'lender' } },
  { key: 'vendors', filters: { company_type: 'vendor' } },
  { key: 'prospects', filters: { status: 'prospect' } },
  { key: 'archived', filters: { include_archived: true, status: 'archived' } },
] as const;

export const PROFILE_TYPES_BY_COMPANY_TYPE: Partial<Record<CrmCompanyType, string>> = {
  investment_company: 'investment_profile',
  buyer_entity: 'investment_profile',
  brokerage: 'brokerage_profile',
  lender: 'lender_profile',
  bank: 'lender_profile',
  vendor: 'vendor_profile',
  law_firm: 'law_firm_profile',
  property_management: 'property_management_profile',
};

// --- CRM Communication Center ---

export type CrmCommChannel =
  | 'email'
  | 'whatsapp'
  | 'sms'
  | 'phone'
  | 'zoom'
  | 'teams'
  | 'meeting'
  | 'internal_message'
  | 'note'
  | 'system_notification'
  | 'other';

export type CrmCommDirection = 'inbound' | 'outbound' | 'internal' | 'system';

export type CrmCommStatus =
  | 'draft'
  | 'scheduled'
  | 'queued'
  | 'sent'
  | 'delivered'
  | 'opened'
  | 'clicked'
  | 'replied'
  | 'failed'
  | 'cancelled'
  | 'archived';

export type CrmCommVisibility = 'private' | 'team' | 'organization' | 'restricted';

export type CrmCommPriority = 'low' | 'medium' | 'high' | 'critical';

export type CrmThreadStatus = 'open' | 'pending' | 'snoozed' | 'closed' | 'archived';

export type CrmCommEntityType =
  | 'contact'
  | 'company'
  | 'opportunity'
  | 'investor'
  | 'property'
  | 'project'
  | 'transaction'
  | 'internal_user'
  | 'relationship';

export type CrmCommThreadSummary = {
  id: string;
  subject: string;
  channel: CrmCommChannel;
  channels: string[] | null;
  unread_count: number;
  message_count: number;
  priority: CrmCommPriority;
  status: CrmThreadStatus;
  tags: string[] | null;
  follow_up_date: string | null;
  last_communication_at: string | null;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  owner_id: string | null;
  assigned_user_id: string | null;
  assigned_team_id: string | null;
  is_pinned: boolean;
  snoozed_until: string | null;
  preview: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type CrmCommSummary = {
  id: string;
  channel: CrmCommChannel;
  direction: CrmCommDirection;
  status: CrmCommStatus;
  subject: string | null;
  preview: string | null;
  thread_id: string | null;
  recipient_entity_type: CrmCommEntityType | null;
  recipient_entity_id: string | null;
  priority: CrmCommPriority;
  visibility: CrmCommVisibility;
  owner_id: string | null;
  assigned_user_id: string | null;
  scheduled_at: string | null;
  sent_at: string | null;
  tags: string[] | null;
  has_attachments: boolean;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type CrmCommDetail = CrmCommSummary & {
  body: string | null;
  body_html: string | null;
  body_text: string | null;
  sender_entity_type: CrmCommEntityType | null;
  sender_entity_id: string | null;
  recipients: Record<string, unknown>[] | null;
  cc_recipients: Record<string, unknown>[] | null;
  bcc_recipients: Record<string, unknown>[] | null;
  participants: Record<string, unknown>[] | null;
  related_entities: Record<string, unknown>[] | null;
  parent_communication_id: string | null;
  external_provider_id: string | null;
  provider_thread_id: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  replied_at: string | null;
  failed_at: string | null;
  failure_reason: string | null;
  assigned_team_id: string | null;
  metadata_json: Record<string, unknown> | null;
  call_duration_seconds: number | null;
  call_outcome: string | null;
  call_direction: string | null;
  meeting_url: string | null;
  meeting_start_at: string | null;
  meeting_end_at: string | null;
  activity_id: string | null;
  attachments: Array<{
    id: string;
    file_name: string;
    file_size: number | null;
    mime_type: string | null;
  }>;
  created_by: string | null;
  updated_by: string | null;
};

export type CrmCommThreadDetail = CrmCommThreadSummary & {
  participant_ids: string[] | null;
  related_entity_ids: Record<string, unknown>[] | null;
  response_time_seconds: number | null;
  sentiment: string | null;
  communications: CrmCommSummary[];
};

export type CrmCommThreadListResponse = {
  items: CrmCommThreadSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
};

export type CrmCommListResponse = {
  items: CrmCommSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
  request_id: string;
};

export type CrmCommTemplateSummary = {
  id: string;
  name: string;
  template_type: string;
  subject: string | null;
  channel: CrmCommChannel | null;
  is_shared: boolean;
  is_active: boolean;
  tags: string[] | null;
  created_at: string;
  updated_at: string;
};

export type CrmCommTemplateDetail = CrmCommTemplateSummary & {
  body: string;
  body_html: string | null;
  variables: string[] | null;
  owner_id: string | null;
  team_id: string | null;
  created_by: string | null;
};

export type CrmCommProviderStatus = {
  provider: string;
  channel: CrmCommChannel;
  status: 'available' | 'unavailable' | 'pending_sync' | 'not_connected';
  message: string | null;
  last_sync_at: string | null;
};

export type CrmCommAnalyticsMetric = {
  key: string;
  label: string;
  value: number | null;
  unavailable: boolean;
  unavailable_reason: string | null;
};

export type CrmCommFolderKey =
  | 'all'
  | 'inbox'
  | 'unread'
  | 'assigned_to_me'
  | 'sent'
  | 'drafts'
  | 'scheduled'
  | 'calls'
  | 'meetings'
  | 'whatsapp'
  | 'sms'
  | 'internal'
  | 'follow_up_due'
  | 'failed'
  | 'archived';

export const CRM_COMM_FOLDERS: { key: CrmCommFolderKey; labelKey: string }[] = [
  { key: 'all', labelKey: 'folders.all' },
  { key: 'inbox', labelKey: 'folders.inbox' },
  { key: 'unread', labelKey: 'folders.unread' },
  { key: 'assigned_to_me', labelKey: 'folders.assignedToMe' },
  { key: 'sent', labelKey: 'folders.sent' },
  { key: 'drafts', labelKey: 'folders.drafts' },
  { key: 'scheduled', labelKey: 'folders.scheduled' },
  { key: 'calls', labelKey: 'folders.calls' },
  { key: 'meetings', labelKey: 'folders.meetings' },
  { key: 'whatsapp', labelKey: 'folders.whatsapp' },
  { key: 'sms', labelKey: 'folders.sms' },
  { key: 'internal', labelKey: 'folders.internal' },
  { key: 'follow_up_due', labelKey: 'folders.followUpDue' },
  { key: 'failed', labelKey: 'folders.failed' },
  { key: 'archived', labelKey: 'folders.archived' },
];

export const CRM_COMM_CHANNELS: CrmCommChannel[] = [
  'email',
  'whatsapp',
  'sms',
  'phone',
  'zoom',
  'teams',
  'meeting',
  'internal_message',
  'note',
];

