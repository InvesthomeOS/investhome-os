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

/** Client generation lifecycle — in-flight placeholders are not completed posts. */
export type SocialPostGenerationLifecycle = 'creating' | 'generating' | 'ready' | 'error';

export const PLACEHOLDER_HEADLINE = 'New social post';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'readingBrief'
  | 'selectingPlatforms'
  | 'writingCaptions'
  | 'designingCreatives'
  | 'optimizing'
  | 'preparingProject'
  | 'writingContent'
  | 'selectingVisual'
  | 'preparingDesign'
  | 'checkingLayout'
  | 'ideogramBrief'
  | 'ideogramSource'
  | 'ideogramGenerating'
  | 'ideogramSaving'
  | 'gptImageBrief'
  | 'gptImageSource'
  | 'gptImageGenerating'
  | 'gptImageSaving'
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

import type { SocialElement } from './social-media-builder-elements';
import { createDefaultElements } from './social-media-builder-elements';

export type { SocialElement } from './social-media-builder-elements';

export type SocialPost = {
  id: string;
  platform: PlatformKey;
  format: ContentFormat;
  formatPreset: FormatPresetKey;
  width: number;
  height: number;
  status: PostStatus;
  /** Legacy filmstrip hint — never Unsplash; prefer coverAssetId. */
  thumbUrl: string;
  name: string;
  /** Synced from headline TEXT element for AI / inspector compat. */
  headline: string;
  description: string;
  /** Synced from body TEXT element. */
  caption: string;
  /** Per-post background / cover Media Library Asset ID. */
  coverAssetId: string | null;
  linkedProjectId: string | null;
  elements: SocialElement[];
  /** Generation metadata — persisted, never rendered on canvas. */
  generationMeta?: Record<string, unknown> | null;
  /** Isolates campaign-only financial facts to this post. */
  campaignContextId?: string | null;
  generationContextId?: string | null;
  createdAt?: string | null;
  updatedAt?: string | null;
  compositionStrategy?: string | null;
  compositionPrimitive?: string | null;
  overlayStrategy?: string | null;
  textAlign?: 'left' | 'center' | 'right' | null;
  safeTextZone?: string | null;
  ctaStrategy?: string | null;
  creativePlan?: Record<string, unknown> | null;
  compositionBlueprint?: Record<string, unknown> | null;
  compositionFamily?: string | null;
  imageCrop?: Record<string, unknown> | null;
  compositionType?: string | null;
  planGeometryLocked?: boolean | null;
  /** In-flight create must not be treated as a completed Gönderi. Not persisted while generating. */
  generationLifecycle?: SocialPostGenerationLifecycle | null;
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

/** Generation-only status stages (existing AI bar styling). Not the demo AI_STATUS_SEQUENCE. */
export const GENERATION_STATUS_STAGES: AiStatusKey[] = [
  'preparingProject',
  'writingContent',
  'selectingVisual',
  'preparingDesign',
  'checkingLayout',
];

/** Visual placeholders only — never used as production artboard media. */
export const SMB_PROJECTS: SmbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Social Launch',
    coverUrl: '',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Social Campaign',
    coverUrl: '',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Awareness',
    coverUrl: '',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus Construction Updates',
    coverUrl: '',
  },
];

export const SMB_TEMPLATES: SmbTemplate[] = [
  { id: 't1', category: 'instagram', thumbUrl: '', format: 'square' },
  { id: 't2', category: 'instagram', thumbUrl: '', format: 'portrait' },
  { id: 't3', category: 'story', thumbUrl: '', format: 'story' },
  { id: 't4', category: 'reels', thumbUrl: '', format: 'reelsCover' },
  { id: 't5', category: 'facebook', thumbUrl: '', format: 'landscape' },
  { id: 't6', category: 'linkedin', thumbUrl: '', format: 'square' },
  { id: 't7', category: 'x', thumbUrl: '', format: 'landscape' },
  { id: 't8', category: 'carousel', thumbUrl: '', format: 'carousel' },
];

function seedPost(partial: Omit<SocialPost, 'elements' | 'coverAssetId' | 'linkedProjectId' | 'thumbUrl'> & {
  thumbUrl?: string;
  coverAssetId?: string | null;
  linkedProjectId?: string | null;
  elements?: SocialElement[];
}): SocialPost {
  const elements =
    partial.elements ??
    createDefaultElements(partial.width, partial.height, {
      headline: partial.headline,
      caption: partial.caption,
    });
  return {
    ...partial,
    thumbUrl: partial.thumbUrl ?? '',
    coverAssetId: partial.coverAssetId ?? null,
    linkedProjectId: partial.linkedProjectId ?? null,
    elements,
  };
}

export const DEFAULT_POSTS: SocialPost[] = [
  seedPost({
    id: 'p1',
    platform: 'instagram',
    format: 'feed',
    formatPreset: 'square',
    width: 1080,
    height: 1080,
    status: 'ready',
    name: 'Square Launch',
    headline: 'Enter THE TEMPLE',
    description: 'Square feed post for Instagram / LinkedIn launch.',
    caption:
      'Washington DC’de zamansız lüks. THE TEMPLE Residences — sınırlı birimlerle özel lansman.',
  }),
  seedPost({
    id: 'p2',
    platform: 'instagram',
    format: 'feed',
    formatPreset: 'portrait',
    width: 1080,
    height: 1350,
    status: 'ready',
    name: 'Portrait Feed',
    headline: 'Quiet Luxury',
    description: '4:5 vertical feed for higher IG reach.',
    caption: 'Mimari zarafet ve yatırım potansiyeli — THE TEMPLE Residences.',
  }),
  seedPost({
    id: 'p3',
    platform: 'facebook',
    format: 'post',
    formatPreset: 'landscape',
    width: 1920,
    height: 1080,
    status: 'draft',
    name: 'Landscape Cover',
    headline: 'Washington DC Opportunity',
    description: '16:9 landscape for Facebook / LinkedIn cover-style posts.',
    caption: 'Discover THE TEMPLE Residences — schedule a private briefing.',
  }),
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
  options?: {
    coverAssetId?: string | null;
    linkedProjectId?: string | null;
    cta?: string;
  },
): SocialPost {
  const size = resolveFormatSize(preset);
  const headline = PLACEHOLDER_HEADLINE;
  const caption = '';
  const elements = createDefaultElements(size.w, size.h, {
    headline,
    caption,
    cta: options?.cta,
  });
  return {
    id: `p-new-${Date.now()}-${index}`,
    platform: 'instagram',
    format:
      preset === 'story'
        ? 'story'
        : preset === 'reelsCover'
          ? 'reel'
          : preset === 'carousel'
            ? 'carousel'
            : 'feed',
    formatPreset: preset,
    width: size.w,
    height: size.h,
    status: 'draft',
    thumbUrl: '',
    name: `New ${preset}`,
    headline,
    description: '',
    caption,
    coverAssetId: options?.coverAssetId ?? null,
    linkedProjectId: options?.linkedProjectId ?? null,
    elements,
    generationLifecycle: 'ready',
  };
}

export function mintCreatePostId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `p-gen-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

/** Isolated in-flight CREATE post — empty canvas, project-scoped, not a completed placeholder. */
export function createGeneratingPost(
  preset: FormatPresetKey,
  index: number,
  options?: { linkedProjectId?: string | null; id?: string },
): SocialPost {
  const size = resolveFormatSize(preset);
  return {
    id: options?.id?.trim() || mintCreatePostId() || `p-gen-${Date.now()}-${index}`,
    platform: 'instagram',
    format:
      preset === 'story'
        ? 'story'
        : preset === 'reelsCover'
          ? 'reel'
          : preset === 'carousel'
            ? 'carousel'
            : 'feed',
    formatPreset: preset,
    width: size.w,
    height: size.h,
    status: 'draft',
    thumbUrl: '',
    name: 'Generating',
    headline: '',
    description: '',
    caption: '',
    coverAssetId: null,
    linkedProjectId: options?.linkedProjectId ?? null,
    elements: [],
    generationLifecycle: 'generating',
  };
}
