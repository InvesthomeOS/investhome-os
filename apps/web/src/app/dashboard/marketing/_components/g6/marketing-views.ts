export const MARKETING_VIEWS = [
  'overview',
  'campaigns',
  'attribution',
  'funnel',
  'lead_sources',
  'website_analytics',
  'seo',
  'content_studio',
  'blog',
  'social',
  'email',
  'paid_ads',
  'landing_pages',
  'calculators',
  'creative_library',
  'calendar',
  'vendors',
  'automations',
  'ai_insights',
  'reports',
] as const;

export type MarketingViewId = (typeof MARKETING_VIEWS)[number];

export function parseView(raw: string | null): MarketingViewId {
  if (raw && (MARKETING_VIEWS as readonly string[]).includes(raw)) {
    return raw as MarketingViewId;
  }
  return 'overview';
}

export type DataKind = 'live' | 'partial' | 'demo' | 'blocked';

/** Honest classification from data audit — not silent mocks. */
export const VIEW_DATA_KIND: Record<MarketingViewId, DataKind> = {
  overview: 'live',
  campaigns: 'live',
  attribution: 'partial',
  funnel: 'live',
  lead_sources: 'live',
  website_analytics: 'partial',
  seo: 'blocked',
  content_studio: 'live',
  blog: 'partial',
  social: 'partial',
  email: 'partial',
  paid_ads: 'blocked',
  landing_pages: 'live',
  calculators: 'partial',
  creative_library: 'live',
  calendar: 'partial',
  vendors: 'blocked',
  automations: 'live',
  ai_insights: 'partial',
  reports: 'live',
};

export const CAMPAIGN_LAYOUTS = ['table', 'cards', 'timeline', 'performance', 'calendar'] as const;
export type CampaignLayout = (typeof CAMPAIGN_LAYOUTS)[number];

export function parseCampaignLayout(raw: string | null): CampaignLayout {
  if (raw && (CAMPAIGN_LAYOUTS as readonly string[]).includes(raw)) {
    return raw as CampaignLayout;
  }
  return 'table';
}

export const DRAWER_SECTIONS = [
  'overview',
  'performance',
  'audience',
  'channels',
  'leads',
  'opportunities',
  'content',
  'ads',
  'budget',
  'activity',
  'documents',
  'ai',
  'audit',
] as const;

export type DrawerSectionId = (typeof DRAWER_SECTIONS)[number];

export const ATTRIBUTION_LABELS = ['full', 'partial', 'unknown', 'untracked'] as const;
export type AttributionLabel = (typeof ATTRIBUTION_LABELS)[number];

export const DEFAULT_FUNNEL_STAGES = [
  'visitor',
  'lead',
  'qualified',
  'meeting',
  'opportunity',
  'reservation',
  'contract',
  'payment',
  'closing',
] as const;
