import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type DevicePreview = 'desktop' | 'tablet' | 'mobile' | 'split';

export type PreviewDevice = Exclude<DevicePreview, 'split'>;

/** Future-ready multi-pane presets (Desktop+Tablet, Tablet+Mobile, all three). */
export type SplitPanePreset =
  | 'desktop-mobile'
  | 'desktop-tablet'
  | 'tablet-mobile'
  | 'desktop-tablet-mobile';

export type PreviewPane = {
  id: string;
  device: PreviewDevice;
};

export type PublishStatus = 'draft' | 'review' | 'approved' | 'published';

export type RightTab =
  | 'properties'
  | 'design'
  | 'seo'
  | 'publishing'
  | 'language'
  | 'quickAi';

export type AssetKind =
  | 'images'
  | 'videos'
  | 'pdf'
  | 'dwg'
  | 'floorPlans'
  | 'logos'
  | 'brand'
  | 'documents'
  | 'brochure'
  | 'investorDeck'
  | 'word'
  | 'powerpoint';

export type AssetSort = 'name' | 'type' | 'recent';

export type AssetUsedIn = 'hero' | 'gallery' | 'homepage' | 'landing' | 'downloads' | 'cta';

export type SectionKey =
  | 'hero'
  | 'about'
  | 'investment'
  | 'gallery'
  | 'floorPlans'
  | 'amenities'
  | 'location'
  | 'faq'
  | 'news'
  | 'cta'
  | 'contact'
  | 'footer';

export type BlockKey =
  | 'gallery'
  | 'timeline'
  | 'statistics'
  | 'pricing'
  | 'maps'
  | 'video'
  | 'testimonials'
  | 'partners'
  | 'cta'
  | 'faq';

export type AiActionKey =
  | 'entireSite'
  | 'currentSection'
  | 'rewrite'
  | 'images'
  | 'seo'
  | 'a11y'
  | 'hero'
  | 'text'
  | 'translate'
  | 'luxury'
  | 'investor'
  | 'simplify'
  | 'expand'
  | 'improveSection'
  | 'generateHero'
  | 'newCta'
  | 'seoOptimize'
  | 'a11yCheck'
  | 'responsiveOptimize'
  | 'performanceAnalysis'
  | 'generateImage'
  | 'changeBackground';

export type MemoryKey =
  | 'project'
  | 'crm'
  | 'photos'
  | 'floorPlans'
  | 'brochures'
  | 'financial'
  | 'brand'
  | 'videos'
  | 'location'
  | 'investorDocs';

export type AiStatusKey =
  | 'idle'
  | 'analyzing'
  | 'readingBrochure'
  | 'generatingHero'
  | 'optimizingMobile'
  | 'seoCompleted'
  | 'imagesGenerated'
  | 'publishingReady';

/** Live progress steps shown during AI generation (req 5). */
export type AiProgressStepKey =
  | 'readingBrand'
  | 'analyzingPhotos'
  | 'readingCrm'
  | 'preparingHero'
  | 'preparingSeo'
  | 'preparingResponsive'
  | 'optimizingPage';

export type LeftSectionKey =
  | 'conversation'
  | 'suggested'
  | 'memory'
  | 'context'
  | 'assets'
  | 'recent';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type EditTarget =
  | 'section'
  | 'text'
  | 'button'
  | 'image'
  | 'hero';

export type PublishCheckKey =
  | 'seo'
  | 'a11y'
  | 'performance'
  | 'brokenLinks'
  | 'responsive'
  | 'analytics'
  | 'cookie'
  | 'ssl'
  | 'domain'
  | 'metadata'
  | 'openGraph'
  | 'schema'
  | 'pageSpeed';

export type DesignAccordionKey =
  | 'hero'
  | 'typography'
  | 'buttons'
  | 'background'
  | 'overlay'
  | 'animation'
  | 'spacing'
  | 'seo'
  | 'accessibility'
  | 'advanced';

export type WbProject = {
  id: ProjectId;
  name: string;
  slug: string;
  featuredLabel: string;
  coverUrl: string;
  galleryUrls: string[];
  city: string;
  stats: { labelKey: 'projects' | 'value' | 'investors' | 'units'; value: string }[];
};

export type WbAsset = {
  id: string;
  kind: AssetKind;
  titleKey: string;
  filename: string;
  fileType: string;
  meta: string;
  resolution?: string;
  folder: string;
  tags: string[];
  thumbUrl?: string;
  usedIn?: AssetUsedIn[];
  updatedAt: string;
};

export type WbSection = {
  id: string;
  key: SectionKey;
  visible: boolean;
  collapsed?: boolean;
  customName?: string;
};

export type WbVersion = {
  id: string;
  label: string;
  status: PublishStatus;
  updatedAt: string;
  noteKey: 'initial' | 'heroRegen' | 'seoPass' | 'luxuryTone' | 'galleryExpand';
  comment?: string;
};

export type WbChatMessage = {
  id: string;
  role: 'ai' | 'user';
  textKey?:
    | 'welcome'
    | 'welcomeBrand'
    | 'welcomeCrm'
    | 'welcomePhotos'
    | 'welcomePlans'
    | 'welcomeBrochures'
    | 'welcomeProject'
    | 'welcomeQuestion'
    | 'userBrief'
    | 'aiReply'
    | 'aiVersion'
    | 'aiCommand';
  text?: string;
};

export type WbPersistedState = {
  projectId: ProjectId;
  selectedSectionId: string;
  device: DevicePreview;
  language: string;
  tone: string;
  publishStatus: PublishStatus;
  sections: WbSection[];
  activeVersionId: string;
  metaTitle: string;
  metaDesc: string;
  slug: string;
  zoom: number;
  splitPreset: SplitPanePreset;
  savedAt: number;
};

export const WB_HOME = '/workspaces/creative-studio';
export const WB_ROUTE = '/workspaces/creative-studio/website-builder';
export const WB_STORAGE_KEY = 'ih-wb-draft-v3';

export const PUBLISH_STATUS_TONE: Record<PublishStatus, StatusChipTone> = {
  draft: 'default',
  review: 'warning',
  approved: 'info',
  published: 'success',
};

export const WORKFLOW_STEPS = ['project', 'structure', 'design', 'content', 'publish'] as const;

export const RIGHT_TABS: RightTab[] = [
  'properties',
  'design',
  'seo',
  'publishing',
  'language',
  'quickAi',
];

export const DEVICE_PREVIEWS: DevicePreview[] = ['desktop', 'tablet', 'mobile', 'split'];

/** Closest IhIcon names — no Monitor/Tablet/Smartphone/Columns in the set. */
export const DEVICE_ICONS: Record<DevicePreview, IhIconName> = {
  desktop: 'design',
  tablet: 'inventory',
  mobile: 'activity',
  split: 'barChart',
};

export const SPLIT_PRESETS: Record<SplitPanePreset, PreviewPane[]> = {
  'desktop-mobile': [
    { id: 'pane-desktop', device: 'desktop' },
    { id: 'pane-mobile', device: 'mobile' },
  ],
  'desktop-tablet': [
    { id: 'pane-desktop', device: 'desktop' },
    { id: 'pane-tablet', device: 'tablet' },
  ],
  'tablet-mobile': [
    { id: 'pane-tablet', device: 'tablet' },
    { id: 'pane-mobile', device: 'mobile' },
  ],
  'desktop-tablet-mobile': [
    { id: 'pane-desktop', device: 'desktop' },
    { id: 'pane-tablet', device: 'tablet' },
    { id: 'pane-mobile', device: 'mobile' },
  ],
};

export const DEFAULT_SPLIT_PRESET: SplitPanePreset = 'desktop-mobile';

export const ZOOM_MIN = 50;
export const ZOOM_MAX = 150;
export const ZOOM_STEP = 10;
export const ZOOM_DEFAULT = 100;

// (req 8) Zoom segmented options.
export const ZOOM_SEGMENTS = [50, 80, 100, 120, 150] as const;

export const ASSET_FILTERS: Array<'all' | AssetKind> = [
  'all',
  'images',
  'videos',
  'pdf',
  'dwg',
  'floorPlans',
  'logos',
  'brand',
  'brochure',
  'investorDeck',
  'word',
  'powerpoint',
  'documents',
];

export const ASSET_SORTS: AssetSort[] = ['name', 'type', 'recent'];

export const ASSET_FOLDERS = ['all', 'renders', 'plans', 'brand', 'docs'] as const;

/** Project Memory chips — Loaded / Not Loaded. */
export const MEMORY_CHIPS: MemoryKey[] = [
  'project',
  'crm',
  'photos',
  'floorPlans',
  'brochures',
  'financial',
  'brand',
  'videos',
  'location',
  'investorDocs',
];

export const MEMORY_READY: MemoryKey[] = [
  'project',
  'crm',
  'photos',
  'floorPlans',
  'brochures',
  'brand',
  'location',
];

export const SUGGESTED_PROMPTS = [
  'premiumSite',
  'templeHome',
  'investorSite',
  'useRenders',
  'optimizeMobile',
] as const;

export const RECENT_PROMPTS = [
  'premiumSite',
  'templeHome',
  'useRenders',
  'investorSite',
] as const;

export const AI_PROGRESS_STEPS: AiProgressStepKey[] = [
  'readingBrand',
  'analyzingPhotos',
  'readingCrm',
  'preparingHero',
  'preparingSeo',
  'preparingResponsive',
  'optimizingPage',
];

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'analyzing',
  'readingBrochure',
  'generatingHero',
  'optimizingMobile',
  'seoCompleted',
  'imagesGenerated',
  'publishingReady',
];

/** Maps generation index to progress step for live checklist UI. */
export const AI_PROGRESS_BY_INDEX: AiProgressStepKey[] = AI_PROGRESS_STEPS;

export const PROJECT_DATA_STATS = {
  photos: 42,
  plans: 12,
  brochures: 3,
} as const;

export const SECTION_ICONS: Record<SectionKey, IhIconName> = {
  hero: 'design',
  about: 'documents',
  investment: 'finance',
  gallery: 'inventory',
  floorPlans: 'projects',
  amenities: 'target',
  location: 'projects',
  faq: 'inbox',
  news: 'activity',
  cta: 'quickAction',
  contact: 'users',
  footer: 'documents',
};

export const DESIGN_ACCORDIONS: DesignAccordionKey[] = [
  'hero',
  'typography',
  'buttons',
  'background',
  'overlay',
  'animation',
  'spacing',
  'seo',
  'accessibility',
  'advanced',
];

/** Context-aware Quick AI actions per section type (req 10). */
export const CONTEXTUAL_AI_BY_SECTION: Record<SectionKey | 'default', AiActionKey[]> = {
  default: ['entireSite', 'seo', 'a11y', 'responsiveOptimize', 'performanceAnalysis'],
  hero: ['generateHero', 'rewrite', 'generateImage', 'changeBackground', 'seoOptimize'],
  about: ['improveSection', 'rewrite', 'translate', 'a11yCheck'],
  investment: ['improveSection', 'rewrite', 'investor', 'seoOptimize'],
  gallery: ['generateImage', 'changeBackground', 'improveSection', 'responsiveOptimize'],
  floorPlans: ['improveSection', 'generateImage', 'a11yCheck'],
  amenities: ['improveSection', 'rewrite', 'expand'],
  location: ['improveSection', 'seoOptimize', 'responsiveOptimize'],
  faq: ['rewrite', 'a11yCheck', 'simplify'],
  news: ['rewrite', 'expand', 'translate'],
  cta: ['newCta', 'rewrite', 'seoOptimize', 'a11yCheck'],
  contact: ['improveSection', 'a11yCheck', 'responsiveOptimize'],
  footer: ['improveSection', 'a11yCheck', 'seoOptimize'],
};

/** Quick AI panel — contextual subset rendered per selected section. */
export const QUICK_AI_ACTIONS: { key: AiActionKey; icon: IhIconName }[] = [
  { key: 'improveSection', icon: 'sparkles' },
  { key: 'rewrite', icon: 'refresh' },
  { key: 'generateHero', icon: 'design' },
  { key: 'newCta', icon: 'quickAction' },
  { key: 'seoOptimize', icon: 'search' },
  { key: 'a11yCheck', icon: 'check' },
  { key: 'responsiveOptimize', icon: 'inventory' },
  { key: 'performanceAnalysis', icon: 'trendingUp' },
  { key: 'generateImage', icon: 'inventory' },
  { key: 'changeBackground', icon: 'design' },
];

export const AI_ACTIONS: { key: AiActionKey; icon: IhIconName }[] = [
  { key: 'entireSite', icon: 'sparkles' },
  { key: 'currentSection', icon: 'design' },
  { key: 'rewrite', icon: 'refresh' },
  { key: 'images', icon: 'inventory' },
  { key: 'seo', icon: 'search' },
  { key: 'a11y', icon: 'check' },
  { key: 'hero', icon: 'design' },
  { key: 'text', icon: 'documents' },
  { key: 'translate', icon: 'activity' },
  { key: 'luxury', icon: 'target' },
  { key: 'investor', icon: 'trendingUp' },
  { key: 'simplify', icon: 'check' },
  { key: 'expand', icon: 'plus' },
];

export const BLOCK_LIBRARY: { key: BlockKey; icon: IhIconName }[] = [
  { key: 'gallery', icon: 'inventory' },
  { key: 'timeline', icon: 'clock' },
  { key: 'statistics', icon: 'barChart' },
  { key: 'pricing', icon: 'finance' },
  { key: 'maps', icon: 'projects' },
  { key: 'video', icon: 'meeting' },
  { key: 'testimonials', icon: 'users' },
  { key: 'partners', icon: 'target' },
  { key: 'cta', icon: 'quickAction' },
  { key: 'faq', icon: 'inbox' },
];

export type SectionActionKey =
  | 'edit'
  | 'duplicate'
  | 'delete'
  | 'rewrite'
  | 'replaceImage'
  | 'move'
  | 'hide'
  | 'preview';

export const SECTION_ACTIONS: { key: SectionActionKey; icon: IhIconName }[] = [
  { key: 'edit', icon: 'design' },
  { key: 'duplicate', icon: 'plus' },
  { key: 'rewrite', icon: 'sparkles' },
  { key: 'move', icon: 'chevronDown' },
  { key: 'hide', icon: 'search' },
  { key: 'delete', icon: 'alert' },
];

export const STRUCTURE_ACTIONS: {
  key: 'edit' | 'duplicate' | 'rewrite' | 'move' | 'hide' | 'delete' | 'collapse';
  icon: IhIconName;
}[] = [
  { key: 'edit', icon: 'design' },
  { key: 'duplicate', icon: 'plus' },
  { key: 'rewrite', icon: 'sparkles' },
  { key: 'move', icon: 'chevronDown' },
  { key: 'hide', icon: 'search' },
  { key: 'delete', icon: 'alert' },
  { key: 'collapse', icon: 'chevronRight' },
];

export const PUBLISH_CHECKS: {
  key: PublishCheckKey;
  icon: IhIconName;
  defaultPass: boolean;
}[] = [
  { key: 'seo', icon: 'search', defaultPass: true },
  { key: 'a11y', icon: 'check', defaultPass: true },
  { key: 'brokenLinks', icon: 'alert', defaultPass: true },
  { key: 'responsive', icon: 'design', defaultPass: true },
  { key: 'performance', icon: 'trendingUp', defaultPass: true },
  { key: 'analytics', icon: 'barChart', defaultPass: true },
  { key: 'cookie', icon: 'documents', defaultPass: true },
  { key: 'metadata', icon: 'documents', defaultPass: true },
  { key: 'openGraph', icon: 'design', defaultPass: true },
  { key: 'schema', icon: 'target', defaultPass: true },
  { key: 'pageSpeed', icon: 'trendingUp', defaultPass: true },
  { key: 'ssl', icon: 'target', defaultPass: true },
  { key: 'domain', icon: 'projects', defaultPass: false },
];

// (req 11) Quality dialog checklist items order.
export const PUBLISH_QUALITY_CHECK_KEYS: PublishCheckKey[] = [
  'seo',
  'a11y',
  'performance',
  'brokenLinks',
  'responsive',
  'analytics',
  'cookie',
];

export const DEFAULT_SECTIONS: WbSection[] = [
  { id: 's-hero', key: 'hero', visible: true },
  { id: 's-about', key: 'about', visible: true },
  { id: 's-investment', key: 'investment', visible: true },
  { id: 's-gallery', key: 'gallery', visible: true },
  { id: 's-floor', key: 'floorPlans', visible: true },
  { id: 's-amenities', key: 'amenities', visible: true },
  { id: 's-location', key: 'location', visible: true },
  { id: 's-faq', key: 'faq', visible: true },
  { id: 's-news', key: 'news', visible: false },
  { id: 's-cta', key: 'cta', visible: true },
  { id: 's-contact', key: 'contact', visible: true },
  { id: 's-footer', key: 'footer', visible: true },
];

/**
 * Collapse accidental structure duplicates from polluted drafts / prior strip→grid migrations.
 * Keeps first id; keeps custom-named inserts (block library); drops bare same-key repeats.
 */
export function normalizeWbSections(sections: WbSection[] | null | undefined): WbSection[] {
  if (!Array.isArray(sections) || sections.length === 0) return DEFAULT_SECTIONS;
  const seenIds = new Set<string>();
  const seenBareKeys = new Set<SectionKey>();
  const out: WbSection[] = [];
  for (const section of sections) {
    if (!section?.id || !section.key) continue;
    if (seenIds.has(section.id)) continue;
    seenIds.add(section.id);
    const bare = !section.customName?.trim();
    if (bare) {
      if (seenBareKeys.has(section.key)) continue;
      seenBareKeys.add(section.key);
    }
    out.push(section);
  }
  return out.length ? out : DEFAULT_SECTIONS;
}

export const WB_PROJECTS: WbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    slug: 'the-temple-residences',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=600&h=400&q=80',
    ],
    city: 'Washington, D.C.',
    stats: [
      { labelKey: 'projects', value: '25+' },
      { labelKey: 'value', value: '$1.2B+' },
      { labelKey: 'investors', value: '4.8K' },
      { labelKey: 'units', value: '186' },
    ],
  },
  {
    id: '309h',
    name: '309 H ST NE',
    slug: '309-h-st-ne',
    featuredLabel: '309 H ST',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1487958449943-2429e8be8625?auto=format&fit=crop&w=600&h=400&q=80',
    ],
    city: 'Washington, D.C.',
    stats: [
      { labelKey: 'projects', value: '25+' },
      { labelKey: 'value', value: '$1.2B+' },
      { labelKey: 'investors', value: '4.8K' },
      { labelKey: 'units', value: '64' },
    ],
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    slug: 'uniloft-dc',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1600607687644-c7171b42498f?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600047509807-ba8f99d2cd00?auto=format&fit=crop&w=600&h=400&q=80',
    ],
    city: 'Washington, D.C.',
    stats: [
      { labelKey: 'projects', value: '25+' },
      { labelKey: 'value', value: '$1.2B+' },
      { labelKey: 'investors', value: '4.8K' },
      { labelKey: 'units', value: '112' },
    ],
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    slug: 'the-campus-3224',
    featuredLabel: 'THE CAMPUS',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&h=900&q=80',
    galleryUrls: [
      'https://images.unsplash.com/photo-1600573472592-401b489a3cdc?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1600047509358-9dc75507daeb?auto=format&fit=crop&w=600&h=400&q=80',
      'https://images.unsplash.com/photo-1512917772905-2f7e50d1b6c0?auto=format&fit=crop&w=600&h=400&q=80',
    ],
    city: 'Washington, D.C.',
    stats: [
      { labelKey: 'projects', value: '25+' },
      { labelKey: 'value', value: '$1.2B+' },
      { labelKey: 'investors', value: '4.8K' },
      { labelKey: 'units', value: '240' },
    ],
  },
];

export const WB_ASSETS: WbAsset[] = [
  {
    id: 'a1',
    kind: 'images',
    titleKey: 'heroNight',
    filename: 'temple-hero.jpg',
    fileType: 'JPG',
    meta: '1920×1080',
    resolution: '1920×1080',
    folder: 'renders',
    tags: ['hero', 'night'],
    thumbUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=200&h=140&q=80',
    usedIn: ['hero', 'homepage', 'downloads'],
    updatedAt: '2h ago',
  },
  {
    id: 'a2',
    kind: 'images',
    titleKey: 'exteriorDay',
    filename: 'exterior-day.jpg',
    fileType: 'JPG',
    meta: '1600×900',
    resolution: '1600×900',
    folder: 'renders',
    tags: ['exterior', 'day'],
    thumbUrl:
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=200&h=140&q=80',
    usedIn: ['gallery', 'homepage'],
    updatedAt: 'Yesterday',
  },
  {
    id: 'a3',
    kind: 'floorPlans',
    titleKey: 'unitA',
    filename: 'floor-plan-01.pdf',
    fileType: 'PDF',
    meta: 'PDF · 2.4 MB',
    folder: 'plans',
    tags: ['floor-plan', 'unit-a'],
    usedIn: ['downloads', 'landing'],
    updatedAt: '3d ago',
  },
  {
    id: 'a4',
    kind: 'pdf',
    titleKey: 'brochure',
    filename: 'investment-brochure.pdf',
    fileType: 'PDF',
    meta: 'PDF · 8.1 MB',
    folder: 'docs',
    tags: ['brochure', 'investor'],
    usedIn: ['downloads', 'landing'],
    updatedAt: '1d ago',
  },
  {
    id: 'a5',
    kind: 'logos',
    titleKey: 'ihLogo',
    filename: 'investhome-logo.svg',
    fileType: 'SVG',
    meta: 'SVG',
    resolution: 'Vector',
    folder: 'brand',
    tags: ['logo', 'brand'],
    usedIn: ['homepage', 'downloads'],
    updatedAt: '1w ago',
  },
  {
    id: 'a6',
    kind: 'videos',
    titleKey: 'drone',
    filename: 'drone-tour.mp4',
    fileType: 'MP4',
    meta: 'MP4 · 0:42',
    folder: 'renders',
    tags: ['drone', 'video'],
    usedIn: ['landing', 'downloads'],
    updatedAt: '4d ago',
  },
  {
    id: 'a7',
    kind: 'dwg',
    titleKey: 'sitePlan',
    filename: 'site-plan.dwg',
    fileType: 'DWG',
    meta: 'DWG · 14 MB',
    folder: 'plans',
    tags: ['dwg', 'site'],
    usedIn: ['downloads'],
    updatedAt: '5d ago',
  },
  {
    id: 'a8',
    kind: 'brand',
    titleKey: 'brandKit',
    filename: 'brand-kit.zip',
    fileType: 'ZIP',
    meta: 'Ready',
    folder: 'brand',
    tags: ['brand-kit'],
    usedIn: ['downloads'],
    updatedAt: '1w ago',
  },
  {
    id: 'a9',
    kind: 'documents',
    titleKey: 'offering',
    filename: 'offering-memo.pdf',
    fileType: 'PDF',
    meta: 'PDF · 3.2 MB',
    folder: 'docs',
    tags: ['offering', 'memo'],
    usedIn: ['landing', 'downloads'],
    updatedAt: '2d ago',
  },
  {
    id: 'a10',
    kind: 'brochure',
    titleKey: 'brochure',
    filename: 'temple-brochure.pdf',
    fileType: 'PDF',
    meta: 'PDF · 6.4 MB',
    folder: 'docs',
    tags: ['brochure', 'print'],
    usedIn: ['downloads', 'landing'],
    updatedAt: '1d ago',
  },
  {
    id: 'a11',
    kind: 'investorDeck',
    titleKey: 'offering',
    filename: 'investor-deck.pptx',
    fileType: 'PPTX',
    meta: 'PowerPoint · 12 MB',
    folder: 'docs',
    tags: ['investor', 'deck'],
    usedIn: ['downloads', 'landing'],
    updatedAt: '3d ago',
  },
  {
    id: 'a12',
    kind: 'word',
    titleKey: 'offering',
    filename: 'project-summary.docx',
    fileType: 'DOCX',
    meta: 'Word · 1.1 MB',
    folder: 'docs',
    tags: ['summary', 'copy'],
    usedIn: ['downloads'],
    updatedAt: '4d ago',
  },
];

export const WB_VERSIONS: WbVersion[] = [
  {
    id: 'v4',
    label: 'v0.4',
    status: 'draft',
    updatedAt: '09:18',
    noteKey: 'luxuryTone',
    comment: 'Luxury tone pass on hero + investment.',
  },
  {
    id: 'v3',
    label: 'v0.3',
    status: 'review',
    updatedAt: '08:42',
    noteKey: 'seoPass',
    comment: 'SEO meta + OG from project cover.',
  },
  {
    id: 'v2',
    label: 'v0.2',
    status: 'draft',
    updatedAt: 'Yesterday',
    noteKey: 'heroRegen',
  },
  {
    id: 'v1',
    label: 'v0.1',
    status: 'draft',
    updatedAt: '2d ago',
    noteKey: 'initial',
    comment: 'Default Investhome template · THE TEMPLE featured.',
  },
];

export const WB_CHAT: WbChatMessage[] = [
  { id: 'm1', role: 'ai', textKey: 'welcomeBrand' },
  { id: 'm2', role: 'ai', textKey: 'welcomeCrm' },
  { id: 'm3', role: 'ai', textKey: 'welcomePhotos' },
  { id: 'm4', role: 'ai', textKey: 'welcomePlans' },
  { id: 'm5', role: 'ai', textKey: 'welcomeBrochures' },
  { id: 'm6', role: 'ai', textKey: 'welcomeProject' },
  { id: 'm7', role: 'ai', textKey: 'welcomeQuestion' },
];

export const PUBLISH_EXPORTS = ['sharePreview', 'exportHtml', 'exportNext', 'exportStatic'] as const;

export const VERSION_ACTIONS = [
  'restore',
  'compare',
  'rename',
  'duplicate',
  'branch',
  'comment',
] as const;

export const KEYBOARD_SHORTCUTS = [
  { keys: '⌘/Ctrl+S', actionKey: 'save' },
  { keys: '⌘/Ctrl+Z', actionKey: 'undo' },
  { keys: '⌘/Ctrl+Shift+Z', actionKey: 'redo' },
  { keys: '⌘/Ctrl+P', actionKey: 'preview' },
  { keys: '1–4', actionKey: 'viewport' },
] as const;

export function getProject(id: ProjectId): WbProject {
  return WB_PROJECTS.find((p) => p.id === id) ?? WB_PROJECTS[0];
}

export function loadPersistedDraft(): WbPersistedState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(WB_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as WbPersistedState;
    if (!parsed?.projectId || !Array.isArray(parsed.sections)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function savePersistedDraft(state: WbPersistedState): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(WB_STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore quota */
  }
}
