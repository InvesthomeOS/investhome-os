import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus =
  | 'draft'
  | 'ready'
  | 'scheduled'
  | 'published'
  | 'failed'
  | 'needsApproval';

export type PlatformKey = 'instagram' | 'facebook' | 'linkedin' | 'x';

export type ContentFormat =
  | 'feed'
  | 'story'
  | 'reel'
  | 'carousel'
  | 'post'
  | 'short'
  | 'video'
  | 'thread';

export type PostStatus = 'ready' | 'draft' | 'scheduled' | 'review';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'readingBrief'
  | 'selectingPlatforms'
  | 'writingCaptions'
  | 'designingCreatives'
  | 'optimizing'
  | 'completed';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type SmbLeftRailId =
  | 'templates'
  | 'components'
  | 'text'
  | 'media'
  | 'brand'
  | 'ai';

export type SmbRightRailId = 'content' | 'style' | 'settings';

export type FormatPresetKey =
  | 'square'
  | 'portrait'
  | 'landscape'
  | 'story'
  | 'reelsCover'
  | 'carousel';

export type BottomActionKey =
  | 'addComponent'
  | 'text'
  | 'image'
  | 'shape'
  | 'icon'
  | 'button'
  | 'video'
  | 'divider'
  | 'social'
  | 'table'
  | 'counter'
  | 'iconText'
  | 'other';

export type FloatingActionKey = 'edit' | 'copy' | 'delete' | 'layer' | 'align';

export type TemplateCategoryKey =
  | 'all'
  | 'instagram'
  | 'facebook'
  | 'linkedin'
  | 'x'
  | 'story'
  | 'reels'
  | 'carousel';

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
  | 'social'
  | 'video'
  | 'iconText'
  | 'counter'
  | 'table'
  | 'logo'
  | 'cta'
  | 'ai'
  | 'qr'
  | 'sticker';

export type SocialPost = {
  id: string;
  platform: PlatformKey;
  format: ContentFormat;
  formatPreset: FormatPresetKey;
  width: number;
  height: number;
  status: PostStatus;
  thumbUrl: string;
  name: string;
  headline: string;
  description: string;
  caption: string;
};

export type SmbProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  coverUrl: string;
};

export type SmbTemplate = {
  id: string;
  category: Exclude<TemplateCategoryKey, 'all'>;
  thumbUrl: string;
  format: FormatPresetKey;
};

export const SMB_HOME = '/workspaces/creative-studio';
export const SMB_ROUTE = '/workspaces/creative-studio/social-media-builder';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  ready: 'success',
  scheduled: 'info',
  published: 'success',
  failed: 'danger',
  needsApproval: 'warning',
};

export const SMB_LEFT_RAIL_IDS: SmbLeftRailId[] = [
  'templates',
  'components',
  'text',
  'media',
  'brand',
  'ai',
];

export const SMB_LEFT_RAIL_ICONS: Record<SmbLeftRailId, IhIconName> = {
  templates: 'inventory',
  components: 'documents',
  text: 'marketing',
  media: 'design',
  brand: 'theme',
  ai: 'sparkles',
};

export const SMB_RIGHT_RAIL_IDS: SmbRightRailId[] = ['content', 'style', 'settings'];

export const SMB_RIGHT_RAIL_ICONS: Record<SmbRightRailId, IhIconName> = {
  content: 'documents',
  style: 'design',
  settings: 'settings',
};

export const SMB_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const FORMAT_PRESETS: {
  key: FormatPresetKey;
  width: number;
  height: number;
}[] = [
  { key: 'square', width: 1080, height: 1080 },
  { key: 'portrait', width: 1080, height: 1350 },
  { key: 'landscape', width: 1920, height: 1080 },
  { key: 'story', width: 1080, height: 1920 },
  { key: 'reelsCover', width: 1080, height: 1920 },
  { key: 'carousel', width: 1080, height: 1080 },
];

export const FORMAT_CONTENT: Record<FormatPresetKey, { w: number; h: number }> = {
  square: { w: 1080, h: 1080 },
  portrait: { w: 1080, h: 1350 },
  landscape: { w: 1920, h: 1080 },
  story: { w: 1080, h: 1920 },
  reelsCover: { w: 1080, h: 1920 },
  carousel: { w: 1080, h: 1080 },
};

export const INSPECTOR_PLATFORMS: { key: PlatformKey; icon: IhIconName }[] = [
  { key: 'instagram', icon: 'activity' },
  { key: 'facebook', icon: 'users' },
  { key: 'linkedin', icon: 'trendingUp' },
  { key: 'x', icon: 'activity' },
];

export const TEMPLATE_CATEGORIES: TemplateCategoryKey[] = [
  'all',
  'instagram',
  'facebook',
  'linkedin',
  'x',
  'story',
  'reels',
  'carousel',
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
  { key: 'shape', icon: 'design' },
  { key: 'icon', icon: 'sparkles' },
  { key: 'button', icon: 'quickAction' },
  { key: 'video', icon: 'meeting' },
  { key: 'divider', icon: 'activity' },
  { key: 'social', icon: 'users' },
  { key: 'table', icon: 'inventory' },
  { key: 'counter', icon: 'barChart' },
  { key: 'iconText', icon: 'marketing' },
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
      { key: 'social', icon: 'users' },
    ],
  },
  {
    group: 'layout',
    items: [
      { key: 'logo', icon: 'theme' },
      { key: 'cta', icon: 'quickAction' },
      { key: 'sticker', icon: 'sparkles' },
    ],
  },
  {
    group: 'content',
    items: [
      { key: 'video', icon: 'meeting' },
      { key: 'iconText', icon: 'marketing' },
      { key: 'counter', icon: 'barChart' },
      { key: 'table', icon: 'inventory' },
    ],
  },
  {
    group: 'advanced',
    items: [
      { key: 'ai', icon: 'sparkles' },
      { key: 'qr', icon: 'target' },
    ],
  },
];

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'thinking',
  'readingBrief',
  'selectingPlatforms',
  'writingCaptions',
  'designingCreatives',
  'optimizing',
  'completed',
];

const THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=720&h=1280&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=720&h=400&q=80',
  'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=720&h=900&q=80',
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=720&h=1280&q=80',
  'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=720&h=400&q=80',
];

export const SMB_PROJECTS: SmbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Social Launch',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Social Campaign',
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
    campaignName: 'Campus Construction Updates',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&h=1600&q=85',
  },
];

export const SMB_TEMPLATES: SmbTemplate[] = [
  { id: 't1', category: 'instagram', thumbUrl: THUMBS[0]!, format: 'square' },
  { id: 't2', category: 'instagram', thumbUrl: THUMBS[1]!, format: 'portrait' },
  { id: 't3', category: 'story', thumbUrl: THUMBS[6]!, format: 'story' },
  { id: 't4', category: 'reels', thumbUrl: THUMBS[2]!, format: 'reelsCover' },
  { id: 't5', category: 'facebook', thumbUrl: THUMBS[4]!, format: 'landscape' },
  { id: 't6', category: 'linkedin', thumbUrl: THUMBS[5]!, format: 'square' },
  { id: 't7', category: 'x', thumbUrl: THUMBS[7]!, format: 'landscape' },
  { id: 't8', category: 'carousel', thumbUrl: THUMBS[3]!, format: 'carousel' },
];

export const DEFAULT_POSTS: SocialPost[] = [
  {
    id: 'p1',
    platform: 'instagram',
    format: 'feed',
    formatPreset: 'square',
    width: 1080,
    height: 1080,
    status: 'ready',
    thumbUrl: THUMBS[0]!,
    name: 'Square Launch',
    headline: 'Enter THE TEMPLE',
    description: 'Square feed post for Instagram / LinkedIn launch.',
    caption:
      'Washington DC’de zamansız lüks. THE TEMPLE Residences — sınırlı birimlerle özel lansman.',
  },
  {
    id: 'p2',
    platform: 'instagram',
    format: 'feed',
    formatPreset: 'portrait',
    width: 1080,
    height: 1350,
    status: 'ready',
    thumbUrl: THUMBS[1]!,
    name: 'Portrait Feed',
    headline: 'Quiet Luxury',
    description: '4:5 vertical feed for higher IG reach.',
    caption: 'Mimari zarafet ve yatırım potansiyeli — THE TEMPLE Residences.',
  },
  {
    id: 'p3',
    platform: 'facebook',
    format: 'post',
    formatPreset: 'landscape',
    width: 1920,
    height: 1080,
    status: 'draft',
    thumbUrl: THUMBS[4]!,
    name: 'Landscape Cover',
    headline: 'Washington DC Opportunity',
    description: '16:9 landscape for Facebook / LinkedIn cover-style posts.',
    caption: 'Discover THE TEMPLE Residences — schedule a private briefing.',
  },
  {
    id: 'p4',
    platform: 'instagram',
    format: 'story',
    formatPreset: 'story',
    width: 1080,
    height: 1920,
    status: 'ready',
    thumbUrl: THUMBS[6]!,
    name: 'Story Invite',
    headline: 'Private Launch',
    description: '9:16 story with safe-area CTA.',
    caption: 'Swipe up · Özel tur rezervasyonu',
  },
  {
    id: 'p5',
    platform: 'instagram',
    format: 'reel',
    formatPreset: 'reelsCover',
    width: 1080,
    height: 1920,
    status: 'ready',
    thumbUrl: THUMBS[2]!,
    name: 'Reels Cover',
    headline: 'Lobby Arrival',
    description: 'Reels cover frame — vertical cinematic still.',
    caption: 'İlk izlenim: THE TEMPLE lobisi.',
  },
  {
    id: 'p6',
    platform: 'instagram',
    format: 'carousel',
    formatPreset: 'carousel',
    width: 1080,
    height: 1080,
    status: 'draft',
    thumbUrl: THUMBS[3]!,
    name: 'Carousel Pack',
    headline: 'Residence Highlights',
    description: 'Multi-slide carousel pack for amenities story.',
    caption: '1/5 · Suites · Amenities · Views · Investment · Contact',
  },
  {
    id: 'p7',
    platform: 'linkedin',
    format: 'post',
    formatPreset: 'square',
    width: 1080,
    height: 1080,
    status: 'scheduled',
    thumbUrl: THUMBS[5]!,
    name: 'LinkedIn Square',
    headline: 'Investor Briefing',
    description: 'LinkedIn investor-facing square creative.',
    caption: 'Capital resilience meets design quality at THE TEMPLE.',
  },
];

export const BRAND_COLORS = ['#0F172A', '#1F4B99', '#C4A574', '#F5F1EA', '#FFFFFF'] as const;

export function getProject(id: ProjectId): SmbProject {
  return SMB_PROJECTS.find((p) => p.id === id) ?? SMB_PROJECTS[0]!;
}

export function formatDimensions(w: number, h: number): string {
  return `${w} × ${h}`;
}

export function aspectThumbClass(preset: FormatPresetKey): string {
  if (preset === 'story' || preset === 'reelsCover') return 'smb-ws__page-thumb--story';
  if (preset === 'portrait') return 'smb-ws__page-thumb--portrait';
  if (preset === 'landscape') return 'smb-ws__page-thumb--landscape';
  return 'smb-ws__page-thumb--aspect';
}

export function resolveFormatSize(key: FormatPresetKey): { w: number; h: number } {
  return FORMAT_CONTENT[key];
}

export function createPostFromPreset(
  preset: FormatPresetKey,
  index: number,
  coverUrl: string,
): SocialPost {
  const size = resolveFormatSize(preset);
  return {
    id: `p-new-${Date.now()}-${index}`,
    platform: 'instagram',
    format: preset === 'story' ? 'story' : preset === 'reelsCover' ? 'reel' : preset === 'carousel' ? 'carousel' : 'feed',
    formatPreset: preset,
    width: size.w,
    height: size.h,
    status: 'draft',
    thumbUrl: coverUrl,
    name: `New ${preset}`,
    headline: 'New social post',
    description: '',
    caption: '',
  };
}
