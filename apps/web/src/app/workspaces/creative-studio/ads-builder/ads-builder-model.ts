import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus =
  | 'draft'
  | 'ready'
  | 'scheduled'
  | 'published'
  | 'failed'
  | 'needsApproval';

export type PlatformKey = 'facebook' | 'instagram' | 'google' | 'linkedin';

export type AdFormatKey = 'square' | 'story' | 'reel' | 'banner' | 'display';

export type AdStatus = 'ready' | 'draft' | 'scheduled' | 'review';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type AdsLeftRailId =
  | 'ads'
  | 'templates'
  | 'components'
  | 'text'
  | 'media'
  | 'brand'
  | 'settings';

export type AdsRightRailId = 'content' | 'targeting' | 'pixel' | 'settings';

export type BottomActionKey =
  | 'addComponent'
  | 'text'
  | 'image'
  | 'video'
  | 'shape'
  | 'icon'
  | 'cta'
  | 'audience'
  | 'pixel'
  | 'counter'
  | 'divider'
  | 'table'
  | 'other';

export type FloatingActionKey = 'edit' | 'copy' | 'delete' | 'layer' | 'align';

export type TemplateCategoryKey =
  | 'all'
  | 'facebook'
  | 'instagram'
  | 'google'
  | 'linkedin'
  | 'story'
  | 'reel'
  | 'banner';

export type BgMode = 'color' | 'image' | 'gradient';

export type ComponentGroupKey = 'basic' | 'layout' | 'content' | 'advanced';

export type ComponentItemKey =
  | 'title'
  | 'text'
  | 'image'
  | 'button'
  | 'shape'
  | 'icon'
  | 'divider'
  | 'video'
  | 'counter'
  | 'table'
  | 'logo'
  | 'cta'
  | 'audience'
  | 'pixel'
  | 'qr';

export type CtaKey =
  | 'learnMore'
  | 'bookTour'
  | 'contact'
  | 'apply'
  | 'shopNow'
  | 'signUp';

export type AdCreative = {
  id: string;
  platform: PlatformKey;
  format: AdFormatKey;
  width: number;
  height: number;
  status: AdStatus;
  thumbUrl: string;
  name: string;
  headline: string;
  description: string;
  cta: CtaKey;
  targetUrl: string;
};

export type AdsProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  coverUrl: string;
};

export type AdsTemplate = {
  id: string;
  category: Exclude<TemplateCategoryKey, 'all'>;
  thumbUrl: string;
  format: AdFormatKey;
};

export const ADS_HOME = '/workspaces/creative-studio';
export const ADS_ROUTE = '/workspaces/creative-studio/ads-builder';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  ready: 'success',
  scheduled: 'info',
  published: 'success',
  failed: 'danger',
  needsApproval: 'warning',
};

export const AD_STATUS_TONE: Record<AdStatus, StatusChipTone> = {
  ready: 'success',
  draft: 'default',
  scheduled: 'info',
  review: 'warning',
};

export const ADS_LEFT_RAIL_IDS: AdsLeftRailId[] = [
  'ads',
  'templates',
  'components',
  'text',
  'media',
  'brand',
  'settings',
];

export const ADS_LEFT_RAIL_ICONS: Record<AdsLeftRailId, IhIconName> = {
  ads: 'trendingUp',
  templates: 'inventory',
  components: 'documents',
  text: 'marketing',
  media: 'design',
  brand: 'theme',
  settings: 'settings',
};

export const ADS_RIGHT_RAIL_IDS: AdsRightRailId[] = [
  'content',
  'targeting',
  'pixel',
  'settings',
];

export const ADS_RIGHT_RAIL_ICONS: Record<AdsRightRailId, IhIconName> = {
  content: 'documents',
  targeting: 'target',
  pixel: 'activity',
  settings: 'settings',
};

export const ADS_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const FORMAT_PRESETS: {
  key: AdFormatKey;
  width: number;
  height: number;
}[] = [
  { key: 'square', width: 1080, height: 1080 },
  { key: 'story', width: 1080, height: 1920 },
  { key: 'reel', width: 1080, height: 1920 },
  { key: 'banner', width: 1200, height: 628 },
  { key: 'display', width: 300, height: 250 },
];

export const FORMAT_CONTENT: Record<AdFormatKey, { w: number; h: number }> = {
  square: { w: 1080, h: 1080 },
  story: { w: 1080, h: 1920 },
  reel: { w: 1080, h: 1920 },
  banner: { w: 1200, h: 628 },
  display: { w: 300, h: 250 },
};

export const PLATFORM_OPTIONS: { key: PlatformKey; icon: IhIconName }[] = [
  { key: 'facebook', icon: 'users' },
  { key: 'instagram', icon: 'activity' },
  { key: 'google', icon: 'search' },
  { key: 'linkedin', icon: 'trendingUp' },
];

export const TEMPLATE_CATEGORIES: TemplateCategoryKey[] = [
  'all',
  'facebook',
  'instagram',
  'google',
  'linkedin',
  'story',
  'reel',
  'banner',
];

export const FLOATING_ACTIONS: { key: FloatingActionKey; icon: IhIconName }[] = [
  { key: 'edit', icon: 'design' },
  { key: 'copy', icon: 'documents' },
  { key: 'delete', icon: 'activity' },
  { key: 'layer', icon: 'inventory' },
  { key: 'align', icon: 'target' },
];

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addComponent', icon: 'plus' },
  { key: 'text', icon: 'documents' },
  { key: 'image', icon: 'inventory' },
  { key: 'video', icon: 'meeting' },
  { key: 'shape', icon: 'design' },
  { key: 'icon', icon: 'sparkles' },
  { key: 'cta', icon: 'quickAction' },
  { key: 'audience', icon: 'users' },
  { key: 'pixel', icon: 'activity' },
  { key: 'counter', icon: 'barChart' },
  { key: 'divider', icon: 'activity' },
  { key: 'table', icon: 'inventory' },
  { key: 'other', icon: 'quickAction' },
];

export const COMPONENT_LIBRARY: {
  group: ComponentGroupKey;
  items: { key: ComponentItemKey; icon: IhIconName }[];
}[] = [
  {
    group: 'basic',
    items: [
      { key: 'title', icon: 'marketing' },
      { key: 'text', icon: 'documents' },
      { key: 'image', icon: 'inventory' },
      { key: 'button', icon: 'quickAction' },
      { key: 'shape', icon: 'design' },
      { key: 'icon', icon: 'sparkles' },
      { key: 'divider', icon: 'activity' },
    ],
  },
  {
    group: 'layout',
    items: [
      { key: 'logo', icon: 'theme' },
      { key: 'cta', icon: 'quickAction' },
    ],
  },
  {
    group: 'content',
    items: [
      { key: 'video', icon: 'meeting' },
      { key: 'counter', icon: 'barChart' },
      { key: 'table', icon: 'inventory' },
      { key: 'audience', icon: 'users' },
    ],
  },
  {
    group: 'advanced',
    items: [
      { key: 'pixel', icon: 'activity' },
      { key: 'qr', icon: 'target' },
    ],
  },
];

export const CTA_OPTIONS: CtaKey[] = [
  'learnMore',
  'bookTour',
  'contact',
  'apply',
  'shopNow',
  'signUp',
];

const THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=720&h=1280&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&h=628&q=80',
  'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=600&h=500&q=80',
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=720&h=1280&q=80',
  'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=720&h=400&q=80',
];

export const ADS_PROJECTS: AdsProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Ads Launch',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Lead Gen',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Awareness',
    coverUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus Retargeting',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
];

export const ADS_TEMPLATES: AdsTemplate[] = [
  { id: 't1', category: 'facebook', thumbUrl: THUMBS[0]!, format: 'square' },
  { id: 't2', category: 'instagram', thumbUrl: THUMBS[1]!, format: 'square' },
  { id: 't3', category: 'story', thumbUrl: THUMBS[6]!, format: 'story' },
  { id: 't4', category: 'reel', thumbUrl: THUMBS[2]!, format: 'reel' },
  { id: 't5', category: 'banner', thumbUrl: THUMBS[4]!, format: 'banner' },
  { id: 't6', category: 'google', thumbUrl: THUMBS[5]!, format: 'display' },
  { id: 't7', category: 'linkedin', thumbUrl: THUMBS[3]!, format: 'square' },
  { id: 't8', category: 'instagram', thumbUrl: THUMBS[7]!, format: 'banner' },
];

export const DEFAULT_ADS: AdCreative[] = [
  {
    id: 'a1',
    platform: 'facebook',
    format: 'square',
    width: 1080,
    height: 1080,
    status: 'ready',
    thumbUrl: THUMBS[0]!,
    name: 'Square Launch',
    headline: 'Enter THE TEMPLE',
    description: 'Timeless luxury in Washington DC — limited residences.',
    cta: 'bookTour',
    targetUrl: 'https://investhome.demo/temple',
  },
  {
    id: 'a2',
    platform: 'instagram',
    format: 'story',
    width: 1080,
    height: 1920,
    status: 'ready',
    thumbUrl: THUMBS[6]!,
    name: 'Story Invite',
    headline: 'Private Launch',
    description: 'Swipe-up story with safe-area CTA.',
    cta: 'bookTour',
    targetUrl: 'https://investhome.demo/temple/tour',
  },
  {
    id: 'a3',
    platform: 'instagram',
    format: 'reel',
    width: 1080,
    height: 1920,
    status: 'draft',
    thumbUrl: THUMBS[2]!,
    name: 'Reel Cover',
    headline: 'Lobby Arrival',
    description: 'Vertical cinematic still for Reels.',
    cta: 'learnMore',
    targetUrl: 'https://investhome.demo/temple',
  },
  {
    id: 'a4',
    platform: 'google',
    format: 'banner',
    width: 1200,
    height: 628,
    status: 'ready',
    thumbUrl: THUMBS[4]!,
    name: 'Banner Awareness',
    headline: 'Washington DC Opportunity',
    description: 'Landscape banner for Google Display / FB.',
    cta: 'learnMore',
    targetUrl: 'https://investhome.demo/temple',
  },
  {
    id: 'a5',
    platform: 'google',
    format: 'display',
    width: 300,
    height: 250,
    status: 'draft',
    thumbUrl: THUMBS[5]!,
    name: 'Display MPU',
    headline: 'Invest in Quiet Luxury',
    description: '300×250 medium rectangle display unit.',
    cta: 'contact',
    targetUrl: 'https://investhome.demo/temple/contact',
  },
  {
    id: 'a6',
    platform: 'linkedin',
    format: 'square',
    width: 1080,
    height: 1080,
    status: 'scheduled',
    thumbUrl: THUMBS[3]!,
    name: 'LinkedIn Square',
    headline: 'Investor Briefing',
    description: 'LinkedIn investor-facing square creative.',
    cta: 'signUp',
    targetUrl: 'https://investhome.demo/temple/investors',
  },
  {
    id: 'a7',
    platform: 'facebook',
    format: 'banner',
    width: 1200,
    height: 628,
    status: 'review',
    thumbUrl: THUMBS[7]!,
    name: 'FB Lead Gen',
    headline: 'Schedule a Private Tour',
    description: 'Lead-gen banner with strong CTA.',
    cta: 'bookTour',
    targetUrl: 'https://investhome.demo/temple/tour',
  },
];

export const BRAND_COLORS = ['#0F172A', '#1F4B99', '#0D9488', '#C4A574', '#FFFFFF'] as const;

export const PERFORMANCE_ESTIMATE = {
  reach: '42K–68K',
  clicks: '1.2K–2.1K',
  ctr: '2.8–3.4%',
} as const;

export function getProject(id: ProjectId): AdsProject {
  return ADS_PROJECTS.find((p) => p.id === id) ?? ADS_PROJECTS[0]!;
}

export function formatDimensions(w: number, h: number): string {
  return `${w} × ${h}`;
}

export function aspectThumbClass(format: AdFormatKey): string {
  if (format === 'story' || format === 'reel') return 'ads-ws__page-thumb--story';
  if (format === 'banner') return 'ads-ws__page-thumb--landscape';
  if (format === 'display') return 'ads-ws__page-thumb--display';
  return 'ads-ws__page-thumb--aspect';
}

export function resolveFormatSize(key: AdFormatKey): { w: number; h: number } {
  return FORMAT_CONTENT[key];
}

export function createAdFromFormat(
  format: AdFormatKey,
  index: number,
  coverUrl: string,
  platform: PlatformKey = 'facebook',
): AdCreative {
  const size = resolveFormatSize(format);
  return {
    id: `a-new-${Date.now()}-${index}`,
    platform,
    format,
    width: size.w,
    height: size.h,
    status: 'draft',
    thumbUrl: coverUrl,
    name: `New ${format}`,
    headline: 'New ad creative',
    description: '',
    cta: 'learnMore',
    targetUrl: 'https://investhome.demo',
  };
}
