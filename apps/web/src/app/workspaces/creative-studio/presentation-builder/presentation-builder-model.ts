import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus = 'draft' | 'ready' | 'exported' | 'archived';

export type LeftSectionKey =
  | 'brief'
  | 'audience'
  | 'presentationType'
  | 'language'
  | 'style'
  | 'duration'
  | 'instructions'
  | 'advanced';

export type PresentationType =
  | 'investor'
  | 'project'
  | 'sales'
  | 'corporate'
  | 'companyProfile'
  | 'investmentDeck'
  | 'financial'
  | 'constructionProgress'
  | 'broker'
  | 'partnership'
  | 'bankFinancing'
  | 'custom';

export type DeckLength = 'short' | 'medium' | 'long';

export type ViewMode = 'slide' | 'outline';

export type AspectRatio = '16:9' | '4:3' | '1:1' | '9:16';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'readingBrief'
  | 'gatheringSources'
  | 'buildingOutline'
  | 'designingSlides'
  | 'writingContent'
  | 'optimizing'
  | 'completed';

export type AiProgressStepKey =
  | 'readingBrief'
  | 'gatheringSources'
  | 'buildingOutline'
  | 'designingSlides'
  | 'writingContent'
  | 'scoringQuality'
  | 'readyToExport';

export type SuggestionKey =
  | 'strongerOpening'
  | 'financialComparison'
  | 'improveCta'
  | 'addInfographic'
  | 'addMap'
  | 'improveTypography'
  | 'shortenDeck';

export type QuickActionKey =
  | 'financialCharts'
  | 'timeline'
  | 'map'
  | 'infographic'
  | 'rewriteAll'
  | 'themeLuxury'
  | 'themeCorporate'
  | 'themeInvestor'
  | 'shortVersion'
  | 'longVersion';

export type ToolbarActionKey =
  | 'addSlide'
  | 'edit'
  | 'rewrite'
  | 'replaceImage'
  | 'changeStyle'
  | 'duplicate'
  | 'delete';

export type ExportOptionKey =
  | 'pptx'
  | 'pdf'
  | 'googleSlides'
  | 'keynote'
  | 'speakerNotes'
  | 'hiresPdf'
  | 'printReadyPdf';

export type SlideKind =
  | 'cover'
  | 'agenda'
  | 'projectOverview'
  | 'location'
  | 'floorPlans'
  | 'investment'
  | 'financials'
  | 'timeline'
  | 'construction'
  | 'lifestyle'
  | 'amenities'
  | 'market'
  | 'comparables'
  | 'risk'
  | 'team'
  | 'cta'
  | 'contact'
  | 'appendix';

export type BrandKitKey = 'logo' | 'primaryColors' | 'typography' | 'slideMaster' | 'watermark';

export type ScoreFactorKey =
  | 'narrativeFlow'
  | 'visualHierarchy'
  | 'dataClarity'
  | 'ctaStrength';

export type ScoreFactorTone = 'good' | 'warn';

export type AiSourceKey =
  | 'crm'
  | 'projects'
  | 'documents'
  | 'mediaLibrary'
  | 'imageBuilder'
  | 'videoBuilder'
  | 'websiteBuilder'
  | 'blogBuilder'
  | 'emailBuilder'
  | 'brandKit'
  | 'floorPlans'
  | 'financialData'
  | 'constructionProgress'
  | 'maps'
  | 'statistics';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type PresentationBrief = {
  presentationType: PresentationType;
  audience: string;
  language: string;
  style: string;
  length: DeckLength;
  goal: string;
  cta: string;
  topic: string;
};

export type PresentationScores = {
  overall: number;
};

export type PbSlide = {
  id: string;
  kind: SlideKind;
  thumbUrl: string;
  titleOverride?: string;
};

export type PbProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  featuredLabel: string;
  coverUrl: string;
};

export const PB_HOME = '/workspaces/creative-studio';
export const PB_ROUTE = '/workspaces/creative-studio/presentation-builder';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  ready: 'success',
  exported: 'info',
  archived: 'warning',
};

export const WORKFLOW_STEPS = [
  'brief',
  'structure',
  'design',
  'slides',
  'animation',
  'publish',
] as const;

export type PbLeftRailId = 'slides' | 'layouts' | 'sections' | 'templates';
export type PbRightRailId = 'theme' | 'brand' | 'animation' | 'notes';

export const PB_LEFT_RAIL_IDS: PbLeftRailId[] = ['slides', 'layouts', 'sections', 'templates'];
export const PB_RIGHT_RAIL_IDS: PbRightRailId[] = ['theme', 'brand', 'animation', 'notes'];

export const BOTTOM_ACTIONS = [
  'addSlide',
  'heading',
  'text',
  'image',
  'chart',
  'table',
  'video',
  'timeline',
  'map',
  'icon',
  'divider',
  'shape',
  'more',
] as const;

/** Component tools on the bottom dock (excludes primary Add Slide). */
export const BOTTOM_COMPONENT_ACTIONS = [
  'heading',
  'text',
  'image',
  'chart',
  'table',
  'video',
  'timeline',
  'map',
  'icon',
  'divider',
  'shape',
  'more',
] as const;

export type BottomActionKey = (typeof BOTTOM_ACTIONS)[number];

export const BOTTOM_ACTION_ICONS: Record<BottomActionKey, IhIconName> = {
  addSlide: 'plus',
  heading: 'design',
  text: 'documents',
  image: 'inventory',
  chart: 'barChart',
  table: 'projects',
  video: 'meeting',
  timeline: 'clock',
  map: 'target',
  icon: 'sparkles',
  divider: 'empty',
  shape: 'theme',
  more: 'quickAction',
};

export const FLOATING_ACTIONS = ['edit', 'copy', 'delete', 'layer', 'align', 'more'] as const;
export type FloatingActionKey = (typeof FLOATING_ACTIONS)[number];

export const FLOATING_ACTION_ICONS: Record<FloatingActionKey, IhIconName> = {
  edit: 'design',
  copy: 'documents',
  delete: 'alert',
  layer: 'projects',
  align: 'target',
  more: 'quickAction',
};

export const LEFT_SECTIONS: LeftSectionKey[] = [
  'brief',
  'audience',
  'presentationType',
  'language',
  'style',
  'duration',
  'instructions',
  'advanced',
];

/** Primary type grid shown in the left panel (concept 2×3 density). */
export const PRESENTATION_TYPES: { key: PresentationType; icon: IhIconName }[] = [
  { key: 'investor', icon: 'trendingUp' },
  { key: 'project', icon: 'projects' },
  { key: 'corporate', icon: 'users' },
  { key: 'investmentDeck', icon: 'barChart' },
  { key: 'sales', icon: 'target' },
  { key: 'financial', icon: 'barChart' },
];

export const PRESENTATION_TYPES_MORE: { key: PresentationType; icon: IhIconName }[] = [
  { key: 'companyProfile', icon: 'documents' },
  { key: 'constructionProgress', icon: 'activity' },
  { key: 'broker', icon: 'users' },
  { key: 'partnership', icon: 'users' },
  { key: 'bankFinancing', icon: 'documents' },
  { key: 'custom', icon: 'sparkles' },
];

export const DECK_LENGTHS: DeckLength[] = ['short', 'medium', 'long'];

export const ASPECT_RATIOS: AspectRatio[] = ['16:9', '4:3', '1:1', '9:16'];

export const LAYOUT_PRESETS = [
  'title',
  'titleBody',
  'twoColumn',
  'imageLeft',
  'imageRight',
  'fullBleed',
  'quote',
  'data',
] as const;

export const SECTION_PRESETS = [
  'opening',
  'project',
  'investment',
  'market',
  'closing',
] as const;

export const TEMPLATE_PRESETS = [
  'investorPitch',
  'salesWalkthrough',
  'boardUpdate',
  'constructionProgress',
  'partnership',
] as const;

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'thinking',
  'readingBrief',
  'gatheringSources',
  'buildingOutline',
  'designingSlides',
  'writingContent',
  'optimizing',
  'completed',
];

export const AI_PROGRESS_STEPS: AiProgressStepKey[] = [
  'readingBrief',
  'gatheringSources',
  'buildingOutline',
  'designingSlides',
  'writingContent',
  'scoringQuality',
  'readyToExport',
];

export const AI_SUGGESTIONS: SuggestionKey[] = [
  'strongerOpening',
  'financialComparison',
  'improveCta',
  'addInfographic',
  'addMap',
];

export const QUICK_ACTIONS: { key: QuickActionKey; icon: IhIconName }[] = [
  { key: 'financialCharts', icon: 'barChart' },
  { key: 'timeline', icon: 'clock' },
  { key: 'map', icon: 'projects' },
  { key: 'infographic', icon: 'design' },
  { key: 'rewriteAll', icon: 'refresh' },
  { key: 'themeLuxury', icon: 'sparkles' },
  { key: 'themeCorporate', icon: 'users' },
  { key: 'themeInvestor', icon: 'target' },
  { key: 'shortVersion', icon: 'activity' },
  { key: 'longVersion', icon: 'documents' },
];

export const TOOLBAR_ACTIONS: { key: ToolbarActionKey; icon: IhIconName }[] = [
  { key: 'addSlide', icon: 'sparkles' },
  { key: 'edit', icon: 'design' },
  { key: 'rewrite', icon: 'refresh' },
  { key: 'replaceImage', icon: 'inventory' },
  { key: 'changeStyle', icon: 'theme' },
  { key: 'duplicate', icon: 'documents' },
  { key: 'delete', icon: 'alert' },
];

export const EXPORT_OPTIONS: ExportOptionKey[] = [
  'pptx',
  'pdf',
  'googleSlides',
  'keynote',
  'speakerNotes',
  'hiresPdf',
  'printReadyPdf',
];

export const PRIMARY_EXPORTS: ExportOptionKey[] = ['pptx', 'pdf', 'googleSlides'];

/** Digital delivery formats (PPTX / PDF / Google Slides). */
export const DIGITAL_EXPORTS: ExportOptionKey[] = ['pptx', 'pdf', 'googleSlides'];

/** Professional / print-oriented exports. */
export const PROFESSIONAL_EXPORTS: ExportOptionKey[] = [
  'hiresPdf',
  'speakerNotes',
  'printReadyPdf',
];

export type PreviewFitMode = 'fit' | 'fill' | 'actual';

export const PREVIEW_FIT_MODES: PreviewFitMode[] = ['fit', 'fill', 'actual'];

/** Estimated minutes by deck length (AI Optimization card). */
export const DURATION_BY_LENGTH: Record<
  DeckLength,
  { estimated: number; ideal: number; recommended: number }
> = {
  short: { estimated: 8, ideal: 8, recommended: 7 },
  medium: { estimated: 11, ideal: 9, recommended: 9 },
  long: { estimated: 18, ideal: 12, recommended: 14 },
};

export const AI_SOURCES: AiSourceKey[] = [
  'crm',
  'projects',
  'documents',
  'mediaLibrary',
  'imageBuilder',
  'videoBuilder',
  'websiteBuilder',
  'blogBuilder',
  'emailBuilder',
  'brandKit',
  'floorPlans',
  'financialData',
  'constructionProgress',
  'maps',
  'statistics',
];

export const BRAND_KIT: BrandKitKey[] = [
  'logo',
  'primaryColors',
  'typography',
  'slideMaster',
  'watermark',
];

export const SCORE_FACTORS: { key: ScoreFactorKey; tone: ScoreFactorTone }[] = [
  { key: 'narrativeFlow', tone: 'good' },
  { key: 'visualHierarchy', tone: 'good' },
  { key: 'dataClarity', tone: 'good' },
  { key: 'ctaStrength', tone: 'warn' },
];

export const STYLE_OPTIONS = [
  'luxuryModern',
  'corporate',
  'minimal',
  'investor',
  'editorial',
] as const;

export const LANGUAGE_OPTIONS = ['en', 'tr', 'bilingual'] as const;

export const EXPORT_QUALITY_OPTIONS = ['standard', 'high', 'print'] as const;

export type ExportQuality = (typeof EXPORT_QUALITY_OPTIONS)[number];

export const DEFAULT_BRIEF: PresentationBrief = {
  presentationType: 'investor',
  audience: 'Institutional investors & family offices',
  language: 'en',
  style: 'luxuryModern',
  length: 'medium',
  goal: 'Secure soft commitments for THE TEMPLE Residences',
  cta: 'Schedule a private investor briefing',
  topic: 'THE TEMPLE Residences — Washington DC Investment Deck',
};

export const DEFAULT_SCORES: PresentationScores = {
  overall: 94,
};

export const PB_PROJECTS: PbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Investor Deck',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Sales Presentation',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Partnership Proposal',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus 3224 Progress Report',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&h=900&q=85',
  },
];

const SLIDE_THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=480&h=270&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=480&h=270&q=80',
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=480&h=270&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=480&h=270&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=480&h=270&q=80',
  'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=480&h=270&q=80',
];

const DEFAULT_SLIDE_KINDS: SlideKind[] = [
  'cover',
  'agenda',
  'projectOverview',
  'location',
  'floorPlans',
  'investment',
  'financials',
  'timeline',
  'construction',
  'lifestyle',
  'amenities',
  'market',
  'comparables',
  'risk',
  'team',
  'cta',
  'contact',
  'appendix',
];

export const DEFAULT_SLIDES: PbSlide[] = DEFAULT_SLIDE_KINDS.map((kind, index) => ({
  id: `sl-${index + 1}`,
  kind,
  thumbUrl: SLIDE_THUMBS[index % SLIDE_THUMBS.length]!,
}));

export function getProject(id: ProjectId): PbProject {
  return PB_PROJECTS.find((p) => p.id === id) ?? PB_PROJECTS[0]!;
}

export function scoreTone(score: number): StatusChipTone {
  if (score >= 90) return 'success';
  if (score >= 75) return 'info';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function reorderSlides(slides: PbSlide[], fromId: string, toId: string): PbSlide[] {
  if (fromId === toId) return slides;
  const fromIndex = slides.findIndex((s) => s.id === fromId);
  const toIndex = slides.findIndex((s) => s.id === toId);
  if (fromIndex < 0 || toIndex < 0) return slides;
  const next = [...slides];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) return slides;
  next.splice(toIndex, 0, moved);
  return next;
}

export function aspectClass(ratio: AspectRatio): string {
  if (ratio === '4:3') return 'is-43';
  if (ratio === '1:1') return 'is-11';
  if (ratio === '9:16') return 'is-916';
  return 'is-169';
}

export function aspectDims(ratio: AspectRatio): { w: number; h: number; aspect: number } {
  if (ratio === '4:3') return { w: 1440, h: 1080, aspect: 4 / 3 };
  if (ratio === '1:1') return { w: 1080, h: 1080, aspect: 1 };
  if (ratio === '9:16') return { w: 1080, h: 1920, aspect: 9 / 16 };
  return { w: 1920, h: 1080, aspect: 16 / 9 };
}
