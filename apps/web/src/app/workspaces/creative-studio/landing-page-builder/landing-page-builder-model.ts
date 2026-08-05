import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type DevicePreview = 'desktop' | 'tablet' | 'mobile' | 'ab';

export type CampaignStatus = 'draft' | 'preview' | 'launch' | 'archived';

export type LeftSectionKey =
  | 'copilot'
  | 'brief'
  | 'assets'
  | 'templates'
  | 'audience'
  | 'recent';

export type LpbLeftRailId = 'components' | 'templates' | 'media' | 'styles' | 'settings';

export type LpbRightRailId = 'page' | 'style' | 'advanced';

export type LpbPageKind = 'home' | 'about' | 'units' | 'gallery' | 'contact' | 'custom';

export type LpbPage = {
  id: string;
  kind: LpbPageKind;
  thumbUrl: string;
};

export type BottomActionKey =
  | 'addSection'
  | 'text'
  | 'gallery'
  | 'video'
  | 'form'
  | 'cta'
  | 'popup'
  | 'code'
  | 'abTest'
  | 'other';

export type ComponentGroupKey = 'basic' | 'content' | 'forms' | 'ecommerce';

export type ComponentItemKey =
  | 'text'
  | 'heading'
  | 'button'
  | 'image'
  | 'video'
  | 'divider'
  | 'spacer'
  | 'icon'
  | 'counter'
  | 'feature'
  | 'service'
  | 'faq'
  | 'team'
  | 'testimonial'
  | 'logo'
  | 'form'
  | 'emailForm'
  | 'contactInfo'
  | 'product'
  | 'cart'
  | 'checkout';

export type RightPanelKey =
  | 'conversion'
  | 'ab'
  | 'cta'
  | 'forms'
  | 'trust'
  | 'seo'
  | 'analytics'
  | 'launch';

export type SectionKey =
  | 'hero'
  | 'benefits'
  | 'roi'
  | 'timeline'
  | 'gallery'
  | 'testimonials'
  | 'faq'
  | 'contact'
  | 'cta'
  | 'footer';

export type CampaignType =
  | 'investor'
  | 'webinar'
  | 'projectLaunch'
  | 'consultation'
  | 'brochure'
  | 'earlyAccess';

export type AiActionKey =
  | 'investorLanding'
  | 'webinar'
  | 'projectLaunch'
  | 'consultation'
  | 'brochure'
  | 'earlyAccess'
  | 'improveCta'
  | 'generateForm'
  | 'insertTrust'
  | 'optimizeConversion'
  | 'improveHero'
  | 'rewriteHeadline'
  | 'increaseConversion'
  | 'generateBetterCta'
  | 'optimizeForm'
  | 'improveMobile'
  | 'reduceBounce'
  | 'generateAlternate';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'summarizingBrief'
  | 'generatingSections'
  | 'optimizingCta'
  | 'scoringConversion'
  | 'completed';

export type AiProgressStepKey =
  | 'readingBrief'
  | 'analyzingAudience'
  | 'buildingHero'
  | 'buildingForm'
  | 'scoringConversion'
  | 'preparingVariants'
  | 'readyToLaunch';

export type AiCompletedWorkKey =
  | 'heroGenerated'
  | 'ctaOptimized'
  | 'formCreated'
  | 'seoOptimized'
  | 'faqGenerated'
  | 'trustSectionAdded';

export type QuickActionKey =
  | 'improveHero'
  | 'rewriteHeadline'
  | 'increaseConversion'
  | 'generateBetterCta'
  | 'optimizeForm'
  | 'improveMobile'
  | 'reduceBounce'
  | 'generateAlternate';

export type LaunchCheckKey =
  | 'seo'
  | 'a11y'
  | 'performance'
  | 'forms'
  | 'cta'
  | 'trust'
  | 'analytics'
  | 'tracking'
  | 'mobile'
  | 'privacy';

export type CtaKey =
  | 'scheduleConsultation'
  | 'downloadPackage'
  | 'becomeInvestor'
  | 'reserveUnit'
  | 'requestInfo'
  | 'bookMeeting';

export type FormFieldKey =
  | 'name'
  | 'email'
  | 'phone'
  | 'country'
  | 'budget'
  | 'timeline'
  | 'interest'
  | 'contactMethod';

export type TrustElementKey =
  | 'testimonials'
  | 'timeline'
  | 'progress'
  | 'maps'
  | 'awards'
  | 'media'
  | 'faq'
  | 'downloads'
  | 'partners';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type AbVariantId = 'a' | 'b' | 'c' | (string & {});

export type LpbSection = {
  id: string;
  key: SectionKey;
  visible: boolean;
};

export type LpbChatMessage = {
  id: string;
  role: 'ai' | 'user';
  textKey?: 'welcome' | 'briefSummary' | 'generated' | 'ctaOptimized' | 'variantCreated';
  text?: string;
};

export type LpbAsset = {
  id: string;
  title: string;
  thumbUrl: string;
  kind: 'image' | 'brochure' | 'logo';
};

export type LpbTemplate = {
  id: string;
  type: CampaignType;
  tint: string;
};

export type AbVariant = {
  id: AbVariantId;
  label: string;
  conversionProb: number;
  noteKey: 'control' | 'betterCta' | 'shorterForm';
  isBest?: boolean;
  thumbTone: 'a' | 'b' | 'c';
  whyKey: 'control' | 'betterCta' | 'shorterForm';
};

export type CampaignBrief = {
  name: string;
  primaryGoal: string;
  audience: string;
  cta: string;
  campaignType: CampaignType;
  trafficSource: string;
  launchReadiness: number;
  structure: string[];
};

export type ConversionScores = {
  overall: number;
  leadQuality: number;
  ctaStrength: number;
  readability: number;
  trust: number;
  seo: number;
  forms: number;
};

export type AnalyticsMetrics = {
  visitors: string;
  conversionRate: string;
  ctaClickRate: string;
  scrollDepth: string;
  bounceRate: string;
  formCompletion: string;
  trafficSources: { label: string; value: string }[];
};

export type LpbProject = {
  id: ProjectId;
  name: string;
  slug: string;
  featuredLabel: string;
  coverUrl: string;
  galleryUrls: string[];
};

export const LPB_HOME = '/workspaces/creative-studio';
export const LPB_ROUTE = '/workspaces/creative-studio/landing-page-builder';
export const LPB_STORAGE_KEY = 'ih-lpb-draft-v1';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  preview: 'info',
  launch: 'success',
  archived: 'warning',
};

export const WORKFLOW_STEPS = ['brief', 'structure', 'optimize', 'abTest', 'launch'] as const;

export const LEFT_SECTIONS: LeftSectionKey[] = [
  'copilot',
  'brief',
  'assets',
  'templates',
  'audience',
  'recent',
];

export const RIGHT_PANELS: RightPanelKey[] = [
  'conversion',
  'ab',
  'cta',
  'forms',
  'trust',
  'seo',
  'analytics',
  'launch',
];

export const DEVICE_PREVIEWS: DevicePreview[] = ['desktop', 'tablet', 'mobile', 'ab'];

export const DEVICE_TOGGLE: Array<'desktop' | 'tablet' | 'mobile'> = [
  'desktop',
  'tablet',
  'mobile',
];

export const DEVICE_ICONS: Record<DevicePreview, IhIconName> = {
  desktop: 'design',
  tablet: 'inventory',
  mobile: 'activity',
  ab: 'barChart',
};

export const LPB_LEFT_RAIL_IDS: LpbLeftRailId[] = [
  'components',
  'templates',
  'media',
  'styles',
  'settings',
];

/** Icon set + order matches Website Builder / Focus Workspace left rail. */
export const LPB_LEFT_RAIL_ICONS: Record<LpbLeftRailId, IhIconName> = {
  components: 'documents',
  templates: 'inventory',
  media: 'design',
  styles: 'settings',
  settings: 'sparkles',
};

export const LPB_RIGHT_RAIL_IDS: LpbRightRailId[] = ['page', 'style', 'advanced'];

/** Icon set order mirrors Website Builder right rail (score → suggestions → quickActions). */
export const LPB_RIGHT_RAIL_ICONS: Record<LpbRightRailId, IhIconName> = {
  page: 'trendingUp',
  style: 'sparkles',
  advanced: 'quickAction',
};

export const LPB_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addSection', icon: 'plus' },
  { key: 'text', icon: 'documents' },
  { key: 'gallery', icon: 'inventory' },
  { key: 'video', icon: 'meeting' },
  { key: 'form', icon: 'inbox' },
  { key: 'cta', icon: 'quickAction' },
  { key: 'popup', icon: 'sparkles' },
  { key: 'code', icon: 'executive' },
  { key: 'abTest', icon: 'barChart' },
  { key: 'other', icon: 'quickAction' },
];

export const COMPONENT_LIBRARY: {
  group: ComponentGroupKey;
  items: { key: ComponentItemKey; icon: IhIconName }[];
}[] = [
  {
    group: 'basic',
    items: [
      { key: 'text', icon: 'documents' },
      { key: 'heading', icon: 'marketing' },
      { key: 'button', icon: 'quickAction' },
      { key: 'image', icon: 'inventory' },
      { key: 'video', icon: 'meeting' },
      { key: 'divider', icon: 'activity' },
      { key: 'spacer', icon: 'empty' },
      { key: 'icon', icon: 'sparkles' },
      { key: 'counter', icon: 'trendingUp' },
    ],
  },
  {
    group: 'content',
    items: [
      { key: 'feature', icon: 'target' },
      { key: 'service', icon: 'projects' },
      { key: 'faq', icon: 'inbox' },
      { key: 'team', icon: 'users' },
      { key: 'testimonial', icon: 'users' },
      { key: 'logo', icon: 'theme' },
    ],
  },
  {
    group: 'forms',
    items: [
      { key: 'form', icon: 'inbox' },
      { key: 'emailForm', icon: 'bell' },
      { key: 'contactInfo', icon: 'users' },
    ],
  },
  {
    group: 'ecommerce',
    items: [
      { key: 'product', icon: 'inventory' },
      { key: 'cart', icon: 'finance' },
      { key: 'checkout', icon: 'check' },
    ],
  },
];

export const STYLE_PRESETS = [
  { id: 'navy', labelKey: 'navy', swatch: '#075b75' },
  { id: 'slate', labelKey: 'slate', swatch: '#1e2b33' },
  { id: 'sand', labelKey: 'sand', swatch: '#c4b49a' },
] as const;

const PAGE_THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&h=260&q=80',
];

export const DEFAULT_PAGES: LpbPage[] = [
  { id: 'pg-home', kind: 'home', thumbUrl: PAGE_THUMBS[0]! },
  { id: 'pg-about', kind: 'about', thumbUrl: PAGE_THUMBS[1]! },
  { id: 'pg-units', kind: 'units', thumbUrl: PAGE_THUMBS[2]! },
  { id: 'pg-gallery', kind: 'gallery', thumbUrl: PAGE_THUMBS[3]! },
  { id: 'pg-contact', kind: 'contact', thumbUrl: PAGE_THUMBS[4]! },
];

export function reorderPages(pages: LpbPage[], fromId: string, toId: string): LpbPage[] {
  if (fromId === toId) return pages;
  const fromIndex = pages.findIndex((p) => p.id === fromId);
  const toIndex = pages.findIndex((p) => p.id === toId);
  if (fromIndex < 0 || toIndex < 0) return pages;
  const next = [...pages];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) return pages;
  next.splice(toIndex, 0, moved);
  return next;
}

export const SECTION_ICONS: Record<SectionKey, IhIconName> = {
  hero: 'design',
  benefits: 'target',
  roi: 'trendingUp',
  timeline: 'clock',
  gallery: 'inventory',
  testimonials: 'users',
  faq: 'inbox',
  contact: 'users',
  cta: 'quickAction',
  footer: 'documents',
};

export const AI_ACTIONS: { key: AiActionKey; icon: IhIconName }[] = [
  { key: 'investorLanding', icon: 'trendingUp' },
  { key: 'webinar', icon: 'meeting' },
  { key: 'projectLaunch', icon: 'projects' },
  { key: 'consultation', icon: 'users' },
  { key: 'brochure', icon: 'documents' },
  { key: 'earlyAccess', icon: 'sparkles' },
  { key: 'improveCta', icon: 'quickAction' },
  { key: 'generateForm', icon: 'inbox' },
  { key: 'insertTrust', icon: 'check' },
  { key: 'optimizeConversion', icon: 'target' },
  { key: 'improveHero', icon: 'design' },
  { key: 'rewriteHeadline', icon: 'sparkles' },
  { key: 'increaseConversion', icon: 'trendingUp' },
  { key: 'generateBetterCta', icon: 'quickAction' },
  { key: 'optimizeForm', icon: 'inbox' },
  { key: 'improveMobile', icon: 'activity' },
  { key: 'reduceBounce', icon: 'target' },
  { key: 'generateAlternate', icon: 'barChart' },
];

export const QUICK_ACTIONS: { key: QuickActionKey; icon: IhIconName }[] = [
  { key: 'improveHero', icon: 'design' },
  { key: 'rewriteHeadline', icon: 'sparkles' },
  { key: 'increaseConversion', icon: 'trendingUp' },
  { key: 'generateBetterCta', icon: 'quickAction' },
  { key: 'optimizeForm', icon: 'inbox' },
  { key: 'improveMobile', icon: 'activity' },
  { key: 'reduceBounce', icon: 'target' },
  { key: 'generateAlternate', icon: 'barChart' },
];

export const AI_COMPLETED_WORK: AiCompletedWorkKey[] = [
  'heroGenerated',
  'ctaOptimized',
  'formCreated',
  'seoOptimized',
  'faqGenerated',
  'trustSectionAdded',
];

export const SUGGESTED_PROMPTS = [
  'investorLanding',
  'webinar',
  'projectLaunch',
  'consultation',
  'brochure',
  'earlyAccess',
] as const;

export const RECENT_PROMPTS = [
  'investorLanding',
  'consultation',
  'brochure',
  'webinar',
] as const;

export const AI_PROGRESS_STEPS: AiProgressStepKey[] = [
  'readingBrief',
  'analyzingAudience',
  'buildingHero',
  'buildingForm',
  'scoringConversion',
  'preparingVariants',
  'readyToLaunch',
];

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'thinking',
  'summarizingBrief',
  'generatingSections',
  'optimizingCta',
  'scoringConversion',
  'completed',
];

export const CTA_OPTIONS: CtaKey[] = [
  'scheduleConsultation',
  'downloadPackage',
  'becomeInvestor',
  'reserveUnit',
  'requestInfo',
  'bookMeeting',
];

export const FORM_FIELDS: FormFieldKey[] = [
  'name',
  'email',
  'phone',
  'country',
  'budget',
  'timeline',
  'interest',
  'contactMethod',
];

export const TRUST_ELEMENTS: { key: TrustElementKey; icon: IhIconName }[] = [
  { key: 'testimonials', icon: 'users' },
  { key: 'timeline', icon: 'clock' },
  { key: 'progress', icon: 'trendingUp' },
  { key: 'maps', icon: 'projects' },
  { key: 'awards', icon: 'target' },
  { key: 'media', icon: 'meeting' },
  { key: 'faq', icon: 'inbox' },
  { key: 'downloads', icon: 'documents' },
  { key: 'partners', icon: 'target' },
];

export const LAUNCH_CHECKS: {
  key: LaunchCheckKey;
  icon: IhIconName;
  defaultPass: boolean;
}[] = [
  { key: 'seo', icon: 'search', defaultPass: true },
  { key: 'a11y', icon: 'check', defaultPass: true },
  { key: 'performance', icon: 'trendingUp', defaultPass: true },
  { key: 'forms', icon: 'inbox', defaultPass: true },
  { key: 'cta', icon: 'quickAction', defaultPass: true },
  { key: 'trust', icon: 'users', defaultPass: true },
  { key: 'analytics', icon: 'barChart', defaultPass: true },
  { key: 'tracking', icon: 'activity', defaultPass: true },
  { key: 'mobile', icon: 'inventory', defaultPass: true },
  { key: 'privacy', icon: 'documents', defaultPass: false },
];

/** Campaign LP rhythm: hero → statistics → benefits → gallery → timeline → testimonials → FAQ → form → CTA */
export const DEFAULT_SECTIONS: LpbSection[] = [
  { id: 's-hero', key: 'hero', visible: true },
  { id: 's-roi', key: 'roi', visible: true },
  { id: 's-benefits', key: 'benefits', visible: true },
  { id: 's-gallery', key: 'gallery', visible: true },
  { id: 's-timeline', key: 'timeline', visible: true },
  { id: 's-testimonials', key: 'testimonials', visible: true },
  { id: 's-faq', key: 'faq', visible: true },
  { id: 's-contact', key: 'contact', visible: true },
  { id: 's-cta', key: 'cta', visible: true },
  { id: 's-footer', key: 'footer', visible: true },
];

export const SECTION_TONE: Partial<Record<SectionKey, 'light' | 'tint' | 'band'>> = {
  hero: 'band',
  roi: 'tint',
  benefits: 'light',
  gallery: 'tint',
  timeline: 'light',
  testimonials: 'tint',
  faq: 'light',
  contact: 'tint',
  cta: 'band',
  footer: 'light',
};

export const LPB_PROJECTS: LpbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    slug: 'the-temple-investor',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=600&h=400&q=80',
    ],
  },
  {
    id: '309h',
    name: '309 H ST NE',
    slug: '309-h-st-ne',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=600&h=400&q=80',
    ],
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    slug: 'uniloft-dc',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=600&h=400&q=80',
    ],
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    slug: 'campus-3224',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=600&h=400&q=80',
    ],
  },
];

export const DEFAULT_BRIEF: CampaignBrief = {
  name: 'The Temple Investor Landing',
  primaryGoal: 'Generate Investor Leads',
  audience: 'High Net Worth Investors',
  cta: 'Schedule a Consultation',
  campaignType: 'investor',
  trafficSource: 'Paid Search + LinkedIn',
  launchReadiness: 92,
  structure: ['hero', 'roi', 'benefits', 'gallery', 'timeline', 'testimonials', 'faq', 'contact', 'cta'],
};

export const DEFAULT_SCORES: ConversionScores = {
  overall: 98,
  leadQuality: 95,
  ctaStrength: 96,
  readability: 94,
  trust: 97,
  seo: 92,
  forms: 92,
};

export const DEFAULT_ANALYTICS: AnalyticsMetrics = {
  visitors: '12.4k',
  conversionRate: '18.9%',
  ctaClickRate: '24.2%',
  scrollDepth: '72%',
  bounceRate: '31%',
  formCompletion: '64%',
  trafficSources: [
    { label: 'Paid Search', value: '38%' },
    { label: 'LinkedIn', value: '27%' },
    { label: 'Email', value: '21%' },
    { label: 'Direct', value: '14%' },
  ],
};

export const AB_VARIANTS: AbVariant[] = [
  {
    id: 'a',
    label: 'Version A',
    conversionProb: 14.2,
    noteKey: 'control',
    thumbTone: 'a',
    whyKey: 'control',
  },
  {
    id: 'b',
    label: 'Version B',
    conversionProb: 18.9,
    noteKey: 'betterCta',
    isBest: true,
    thumbTone: 'b',
    whyKey: 'betterCta',
  },
  {
    id: 'c',
    label: 'Version C',
    conversionProb: 16.1,
    noteKey: 'shorterForm',
    thumbTone: 'c',
    whyKey: 'shorterForm',
  },
];

export const PARTNER_LOGOS = ['Hilton Capital', 'DC Realty', 'Summit Partners', 'Apex Fund'] as const;

export const AWARD_KEYS = ['design', 'delivery', 'investor'] as const;

export const MEDIA_KEYS = ['forbes', 'bizjournal', 'urbanland'] as const;

export const PROGRESS_MILESTONES = [
  { key: 'foundation', pct: 100 },
  { key: 'structure', pct: 72 },
  { key: 'interiors', pct: 38 },
  { key: 'delivery', pct: 12 },
] as const;

export const HERO_TRUST_KEYS = ['verified', 'unitsLeft', 'advisors'] as const;

export const SCORE_CARD_METRICS = [
  { key: 'overall', labelKey: 'conversionScore' },
  { key: 'trust', labelKey: 'trust' },
  { key: 'ctaStrength', labelKey: 'ctaStrength' },
  { key: 'leadQuality', labelKey: 'leadQuality' },
  { key: 'readability', labelKey: 'readability' },
] as const;

export const LPB_ASSETS: LpbAsset[] = [
  {
    id: 'a1',
    title: 'Temple exterior',
    thumbUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=200&h=140&q=80',
    kind: 'image',
  },
  {
    id: 'a2',
    title: 'Lobby render',
    thumbUrl:
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=200&h=140&q=80',
    kind: 'image',
  },
  {
    id: 'a3',
    title: 'Unit interior',
    thumbUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=200&h=140&q=80',
    kind: 'image',
  },
  {
    id: 'a4',
    title: 'Investor package',
    thumbUrl:
      'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=200&h=140&q=80',
    kind: 'brochure',
  },
  {
    id: 'a5',
    title: 'Investhome logo',
    thumbUrl:
      'https://images.unsplash.com/photo-1560179707-f14e90ef3623?auto=format&fit=crop&w=200&h=140&q=80',
    kind: 'logo',
  },
  {
    id: 'a6',
    title: 'Skyline view',
    thumbUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=200&h=140&q=80',
    kind: 'image',
  },
];

export const LPB_TEMPLATES: LpbTemplate[] = [
  { id: 't1', type: 'investor', tint: '#eef6f8' },
  { id: 't2', type: 'projectLaunch', tint: '#f0f7f4' },
  { id: 't3', type: 'webinar', tint: '#f3f6fb' },
  { id: 't4', type: 'consultation', tint: '#f7fafb' },
  { id: 't5', type: 'brochure', tint: '#eef8fa' },
  { id: 't6', type: 'earlyAccess', tint: '#f5f8f9' },
];

export const LPB_CHAT: LpbChatMessage[] = [
  { id: 'c1', role: 'ai', textKey: 'welcome' },
  { id: 'c2', role: 'ai', textKey: 'briefSummary' },
];

export const BENEFIT_KEYS = ['location', 'roi', 'team', 'scarcity'] as const;

export const HERO_STATS = [
  { key: 'location', value: 'Washington, DC' },
  { key: 'roi', value: '12–15% IRR' },
  { key: 'price', value: 'From $485k' },
  { key: 'units', value: '48 units' },
] as const;

export const FAQ_KEYS = ['minimum', 'timeline', 'returns', 'process'] as const;

export const TESTIMONIAL_KEYS = ['t1', 't2'] as const;

export const TIMELINE_KEYS = ['land', 'construction', 'presale', 'delivery'] as const;

export function getProject(id: ProjectId): LpbProject {
  return LPB_PROJECTS.find((p) => p.id === id) ?? LPB_PROJECTS[0];
}

export function scoreTone(score: number): StatusChipTone {
  if (score >= 90) return 'success';
  if (score >= 75) return 'info';
  if (score >= 60) return 'warning';
  return 'danger';
}

export type SectionTrayActionKey =
  | 'edit'
  | 'rewrite'
  | 'replaceImage'
  | 'duplicate'
  | 'hide'
  | 'delete';

export const SECTION_TRAY_ACTIONS: {
  key: SectionTrayActionKey;
  icon: IhIconName;
  primary?: boolean;
}[] = [
  { key: 'edit', icon: 'design', primary: true },
  { key: 'rewrite', icon: 'sparkles', primary: true },
  { key: 'replaceImage', icon: 'inventory' },
  { key: 'duplicate', icon: 'plus' },
  { key: 'hide', icon: 'search' },
  { key: 'delete', icon: 'alert' },
];

export function reorderSections(
  sections: LpbSection[],
  fromId: string,
  toId: string,
): LpbSection[] {
  if (fromId === toId) return sections;
  const fromIndex = sections.findIndex((s) => s.id === fromId);
  const toIndex = sections.findIndex((s) => s.id === toId);
  if (fromIndex < 0 || toIndex < 0) return sections;
  const next = [...sections];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) return sections;
  next.splice(toIndex, 0, moved);
  return next;
}
