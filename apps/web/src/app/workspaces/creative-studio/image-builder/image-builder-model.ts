import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus = 'draft' | 'ready' | 'exported' | 'archived';

export type AspectRatio = '16:9' | '4:3' | '1:1' | '9:16' | '3:4';

export type Resolution = '1024' | '1536' | '2048' | '4k';

export type LeftSectionKey = 'brief' | 'assets' | 'brand' | 'advanced';

export type IbLeftRailId =
  | 'generate'
  | 'edit'
  | 'variation'
  | 'upscale'
  | 'background'
  | 'text'
  | 'elements'
  | 'layers';

export type IbRightRailId = 'aiTools' | 'layers' | 'details' | 'history' | 'export';

export type IbEditTool = 'brush' | 'eraser' | 'inpaint' | 'outpaint';

export type IbBgTool = 'remove' | 'replace' | 'blur' | 'transparency';

export type IbAiToolKey =
  | 'expand'
  | 'removeObject'
  | 'replaceObject'
  | 'bgRemoval'
  | 'colorCorrection'
  | 'relight'
  | 'sharpen'
  | 'magicEraser'
  | 'restore';

export type IbLayer = {
  id: string;
  name: string;
  visible: boolean;
  locked: boolean;
  thumbUrl: string;
};

export type IbHistoryItem = {
  id: string;
  labelKey: string;
  time: string;
};

export type IbImageDetails = {
  resolution: string;
  fileSize: string;
  createdDate: string;
  aiModel: string;
  aspectRatio: string;
  generationTime: string;
};

export type GenerationType =
  | 'realEstate'
  | 'interiorDesign'
  | 'floorPlan'
  | 'architecture'
  | 'marketing'
  | 'socialMedia'
  | 'brochure'
  | 'website'
  | 'product'
  | 'generalAi';

export type FloorPlanMode = 'furnished' | 'plan3d' | 'interiorRender' | 'exteriorRender';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'readingBrief'
  | 'analyzingReferences'
  | 'generatingImages'
  | 'optimizing'
  | 'completed';

export type AiProgressStepKey =
  | 'readingBrief'
  | 'analyzingReferences'
  | 'composingScene'
  | 'generatingImages'
  | 'scoringQuality'
  | 'readyToExport';

export type SuggestionKey =
  | 'dramaticSky'
  | 'treeShadows'
  | 'warmerGoldenHour'
  | 'addLifestylePeople';

export type QuickActionKey =
  | 'moreCinematic'
  | 'moreLuxury'
  | 'betterLighting'
  | 'goldenHour'
  | 'rainVersion'
  | 'nightVersion'
  | 'winterVersion'
  | 'summerVersion'
  | 'replaceSky'
  | 'addPeople'
  | 'addFurniture'
  | 'removeObjects';

export type CanvasQuickActionKey =
  | 'variations'
  | 'edit'
  | 'replaceRegion'
  | 'changeStyle'
  | 'enhance'
  | 'upscale';

export type ExportFormatKey = 'jpg' | 'png' | 'webp' | 'tiff' | 'transparent' | 'hires';

export type PreviewDisplayMode = 'fit' | 'fill' | 'actual' | 'print';

export type ExportPathKey = 'digital' | 'print';

export type PrintResolutionKey = '2048' | '4096' | '8192' | 'custom' | 'upscale2' | 'upscale4';

export type PrintDpiKey = '72' | '150' | '300' | 'custom';

export type PrintUnitKey = 'px' | 'cm' | 'inch';

export type PrintPresetKey =
  | 'a4'
  | 'a3'
  | 'a2'
  | 'a1'
  | 'a0'
  | 'poster'
  | 'brochureCover'
  | 'catalogPage'
  | 'billboard'
  | 'custom';

export type ColorProfileKey = 'srgb' | 'adobeRgb' | 'cmyk';

export type PrintFormatKey = 'jpg' | 'png' | 'tiff' | 'pdf';

export type DigitalFormatKey = 'jpg' | 'png' | 'webp';

export type BleedKey = 'none' | '3mm' | '5mm' | 'custom';

export type PrintReadinessKey =
  | 'printReady'
  | 'needsAttention'
  | 'readyToPrint'
  | 'needsUpscale'
  | 'insufficientDpi'
  | 'cmykRecommended'
  | 'needsX4Upscale';

export type OverlayActionKey = 'zoom' | 'edit' | 'lighting' | 'fullscreen';

export type PrintExportState = {
  path: ExportPathKey;
  resolution: PrintResolutionKey;
  customWidth: number;
  customHeight: number;
  dpi: PrintDpiKey;
  customDpi: number;
  physicalWidth: number;
  physicalHeight: number;
  unit: PrintUnitKey;
  preset: PrintPresetKey;
  colorProfile: ColorProfileKey;
  printFormat: PrintFormatKey;
  digitalFormat: DigitalFormatKey;
  transparentBg: boolean;
  noWatermark: boolean;
  bleed: BleedKey;
  customBleedMm: number;
  cropMarks: boolean;
  safeArea: boolean;
  embedColorProfile: boolean;
  maximumQuality: boolean;
  preserveMetadata: boolean;
};

export type PrintValidation = {
  effectiveDpi: number;
  physicalLabel: string;
  colorProfile: ColorProfileKey;
  estimatedBytes: number;
  sharpness: 'excellent' | 'good' | 'fair' | 'poor';
  enlargementRisk: 'low' | 'medium' | 'high';
  bleedStatus: 'ok' | 'missing' | 'custom';
  safeAreaStatus: 'ok' | 'off';
  messages: PrintReadinessKey[];
  finalState: 'printReady' | 'needsAttention';
};

export type ScoreFactorKey = 'composition' | 'lighting' | 'brandFit' | 'detail';

export type ScoreFactorTone = 'good' | 'warn';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type IbVariation = {
  id: string;
  thumbUrl: string;
  label: string;
};

export type IbProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  featuredLabel: string;
  coverUrl: string;
};

export type ImageBrief = {
  prompt: string;
  style: string;
  lighting: string;
  mood: string;
  targetUsage: string;
  camera: string;
  composition: string;
  seed: string;
  variations: string;
};

export type ImageScores = {
  overall: number;
};

export const IB_HOME = '/workspaces/creative-studio';
export const IB_ROUTE = '/workspaces/creative-studio/image-builder';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  ready: 'success',
  exported: 'info',
  archived: 'warning',
};

export const WORKFLOW_STEPS = ['brief', 'styleRef', 'generate', 'edit', 'export'] as const;

export const LEFT_SECTIONS: LeftSectionKey[] = ['brief', 'assets', 'brand', 'advanced'];

export const IB_LEFT_RAIL_IDS: IbLeftRailId[] = [
  'generate',
  'edit',
  'variation',
  'upscale',
  'background',
  'text',
  'elements',
  'layers',
];

export const IB_LEFT_RAIL_ICONS: Record<IbLeftRailId, IhIconName> = {
  generate: 'sparkles',
  edit: 'design',
  variation: 'refresh',
  upscale: 'trendingUp',
  background: 'theme',
  text: 'documents',
  elements: 'inventory',
  layers: 'projects',
};

export const IB_RIGHT_RAIL_IDS: IbRightRailId[] = [
  'aiTools',
  'layers',
  'details',
  'history',
  'export',
];

export const IB_RIGHT_RAIL_ICONS: Record<IbRightRailId, IhIconName> = {
  aiTools: 'sparkles',
  layers: 'projects',
  details: 'search',
  history: 'clock',
  export: 'inbox',
};

export const IB_EDIT_TOOLS: { key: IbEditTool; icon: IhIconName }[] = [
  { key: 'brush', icon: 'design' },
  { key: 'eraser', icon: 'alert' },
  { key: 'inpaint', icon: 'sparkles' },
  { key: 'outpaint', icon: 'trendingUp' },
];

export const IB_BG_TOOLS: { key: IbBgTool; icon: IhIconName }[] = [
  { key: 'remove', icon: 'alert' },
  { key: 'replace', icon: 'refresh' },
  { key: 'blur', icon: 'empty' },
  { key: 'transparency', icon: 'theme' },
];

export const IB_AI_TOOLS: { key: IbAiToolKey; icon: IhIconName }[] = [
  { key: 'expand', icon: 'trendingUp' },
  { key: 'removeObject', icon: 'alert' },
  { key: 'replaceObject', icon: 'refresh' },
  { key: 'bgRemoval', icon: 'theme' },
  { key: 'colorCorrection', icon: 'design' },
  { key: 'relight', icon: 'sparkles' },
  { key: 'sharpen', icon: 'target' },
  { key: 'magicEraser', icon: 'quickAction' },
  { key: 'restore', icon: 'clock' },
];

export const IB_UPSCALE_OPTIONS = ['2x', '4x'] as const;

export const IB_QUALITY_OPTIONS = ['standard', 'high', 'ultra'] as const;

export const IB_MODEL_OPTIONS = ['ihVision', 'ihPhoto', 'ihRender'] as const;

export const IB_TEXT_ALIGN = ['left', 'center', 'right'] as const;

export const IB_ELEMENT_CATEGORIES = ['shapes', 'icons', 'logos', 'assets'] as const;

export const IB_BOTTOM_ACTIONS = [
  'newImage',
  'addToFolder',
  'favorite',
  'share',
  'more',
] as const;

export type IbBottomAction = (typeof IB_BOTTOM_ACTIONS)[number];

export const IB_BOTTOM_ACTION_ICONS: Record<IbBottomAction, IhIconName> = {
  newImage: 'plus',
  addToFolder: 'inbox',
  favorite: 'check',
  share: 'arrowRight',
  more: 'quickAction',
};

export const IB_FLOATING_ACTIONS = ['edit', 'variation', 'upscale', 'delete'] as const;

export type IbFloatingAction = (typeof IB_FLOATING_ACTIONS)[number];

export const DEFAULT_LAYERS: IbLayer[] = [
  {
    id: 'l1',
    name: 'Background',
    visible: true,
    locked: true,
    thumbUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=120&h=80&q=70',
  },
  {
    id: 'l2',
    name: 'Main render',
    visible: true,
    locked: false,
    thumbUrl:
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=120&h=80&q=70',
  },
  {
    id: 'l3',
    name: 'Overlay text',
    visible: true,
    locked: false,
    thumbUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=120&h=80&q=70',
  },
];

export const DEFAULT_HISTORY: IbHistoryItem[] = [
  { id: 'h1', labelKey: 'generated', time: '2m' },
  { id: 'h2', labelKey: 'upscaled', time: '8m' },
  { id: 'h3', labelKey: 'edited', time: '14m' },
  { id: 'h4', labelKey: 'brief', time: '22m' },
];

export const DEFAULT_IMAGE_DETAILS: IbImageDetails = {
  resolution: '2048 × 1152',
  fileSize: '2.4 MB',
  createdDate: '2026-08-03',
  aiModel: 'IH Vision Pro',
  aspectRatio: '16:9',
  generationTime: '12.4s',
};

export const GENERATION_TYPES: { key: GenerationType; icon: IhIconName }[] = [
  { key: 'realEstate', icon: 'projects' },
  { key: 'interiorDesign', icon: 'design' },
  { key: 'floorPlan', icon: 'inventory' },
  { key: 'architecture', icon: 'projects' },
  { key: 'marketing', icon: 'target' },
  { key: 'socialMedia', icon: 'activity' },
  { key: 'brochure', icon: 'documents' },
  { key: 'website', icon: 'design' },
  { key: 'product', icon: 'inbox' },
  { key: 'generalAi', icon: 'sparkles' },
];

export const FLOOR_PLAN_MODES: FloorPlanMode[] = [
  'furnished',
  'plan3d',
  'interiorRender',
  'exteriorRender',
];

export const ASPECT_RATIOS: AspectRatio[] = ['16:9', '4:3', '1:1', '9:16', '3:4'];

export const RESOLUTIONS: Resolution[] = ['1024', '1536', '2048', '4k'];

export const STYLE_OPTIONS = [
  'luxuryModern',
  'photoreal',
  'editorial',
  'minimal',
  'cinematic',
] as const;

export const LIGHTING_OPTIONS = [
  'goldenHour',
  'softDay',
  'dramatic',
  'studio',
  'night',
] as const;

export const MOOD_OPTIONS = ['premium', 'warm', 'calm', 'bold', 'aspirational'] as const;

export const TARGET_USAGE_OPTIONS = [
  'websiteHero',
  'social',
  'brochure',
  'presentation',
  'ads',
] as const;

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'thinking',
  'readingBrief',
  'analyzingReferences',
  'generatingImages',
  'optimizing',
  'completed',
];

export const AI_PROGRESS_STEPS: AiProgressStepKey[] = [
  'readingBrief',
  'analyzingReferences',
  'composingScene',
  'generatingImages',
  'scoringQuality',
  'readyToExport',
];

export const AI_SUGGESTIONS: SuggestionKey[] = [
  'dramaticSky',
  'treeShadows',
  'warmerGoldenHour',
  'addLifestylePeople',
];

export const QUICK_ACTIONS: { key: QuickActionKey; icon: IhIconName }[] = [
  { key: 'moreCinematic', icon: 'meeting' },
  { key: 'moreLuxury', icon: 'sparkles' },
  { key: 'betterLighting', icon: 'design' },
  { key: 'goldenHour', icon: 'clock' },
  { key: 'rainVersion', icon: 'activity' },
  { key: 'nightVersion', icon: 'theme' },
  { key: 'winterVersion', icon: 'empty' },
  { key: 'summerVersion', icon: 'trendingUp' },
  { key: 'replaceSky', icon: 'refresh' },
  { key: 'addPeople', icon: 'users' },
  { key: 'addFurniture', icon: 'inventory' },
  { key: 'removeObjects', icon: 'alert' },
];

export const CANVAS_QUICK_ACTIONS: { key: CanvasQuickActionKey; icon: IhIconName }[] = [
  { key: 'variations', icon: 'sparkles' },
  { key: 'edit', icon: 'design' },
  { key: 'replaceRegion', icon: 'target' },
  { key: 'changeStyle', icon: 'activity' },
  { key: 'enhance', icon: 'trendingUp' },
  { key: 'upscale', icon: 'barChart' },
];

export const OVERLAY_ACTIONS: { key: OverlayActionKey; icon: IhIconName }[] = [
  { key: 'zoom', icon: 'search' },
  { key: 'edit', icon: 'design' },
  { key: 'lighting', icon: 'sparkles' },
  { key: 'fullscreen', icon: 'trendingUp' },
];

export const EXPORT_FORMATS: ExportFormatKey[] = [
  'jpg',
  'png',
  'webp',
  'tiff',
  'transparent',
  'hires',
];

export const PREVIEW_DISPLAY_MODES: PreviewDisplayMode[] = ['fit', 'fill', 'actual', 'print'];

export const PRINT_RESOLUTIONS: PrintResolutionKey[] = [
  '2048',
  '4096',
  '8192',
  'custom',
  'upscale2',
  'upscale4',
];

export const PRINT_DPI_OPTIONS: PrintDpiKey[] = ['72', '150', '300', 'custom'];

export const PRINT_UNITS: PrintUnitKey[] = ['px', 'cm', 'inch'];

export const PRINT_PRESETS: PrintPresetKey[] = [
  'a4',
  'a3',
  'a2',
  'a1',
  'a0',
  'poster',
  'brochureCover',
  'catalogPage',
  'billboard',
  'custom',
];

export const COLOR_PROFILES: ColorProfileKey[] = ['srgb', 'adobeRgb', 'cmyk'];

export const PRINT_FORMATS: PrintFormatKey[] = ['jpg', 'png', 'tiff', 'pdf'];

export const DIGITAL_FORMATS: DigitalFormatKey[] = ['jpg', 'png', 'webp'];

export const BLEED_OPTIONS: BleedKey[] = ['none', '3mm', '5mm', 'custom'];

export const DIGITAL_PRESETS = [
  'instagramPost',
  'instagramStory',
  'linkedin',
  'websiteHero',
  'webBanner',
] as const;

export type DigitalPresetKey = (typeof DIGITAL_PRESETS)[number];

/** Physical size in inches for each print preset (width × height). */
export const PRINT_PRESET_INCHES: Record<Exclude<PrintPresetKey, 'custom'>, [number, number]> = {
  a4: [8.27, 11.69],
  a3: [11.69, 16.54],
  a2: [16.54, 23.39],
  a1: [23.39, 33.11],
  a0: [33.11, 46.81],
  poster: [24, 36],
  brochureCover: [8.27, 11.69],
  catalogPage: [8.5, 11],
  billboard: [96, 48],
};

export const DEFAULT_PRINT_EXPORT: PrintExportState = {
  path: 'digital',
  resolution: '4096',
  customWidth: 4096,
  customHeight: 2304,
  dpi: '300',
  customDpi: 300,
  physicalWidth: 8.27,
  physicalHeight: 11.69,
  unit: 'inch',
  preset: 'a4',
  colorProfile: 'srgb',
  printFormat: 'tiff',
  digitalFormat: 'jpg',
  transparentBg: false,
  noWatermark: true,
  bleed: '3mm',
  customBleedMm: 3,
  cropMarks: true,
  safeArea: true,
  embedColorProfile: true,
  maximumQuality: true,
  preserveMetadata: true,
};

export const SCORE_FACTORS: { key: ScoreFactorKey; tone: ScoreFactorTone }[] = [
  { key: 'composition', tone: 'good' },
  { key: 'lighting', tone: 'good' },
  { key: 'brandFit', tone: 'good' },
  { key: 'detail', tone: 'warn' },
];

export const REFERENCE_THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=160&h=120&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=160&h=120&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=160&h=120&q=80',
];

export const DEFAULT_BRIEF: ImageBrief = {
  prompt:
    'Modern luxury apartment exterior at sunset in Washington DC — warm golden light, glass façade, landscaped plaza, premium real estate render.',
  style: 'luxuryModern',
  lighting: 'goldenHour',
  mood: 'premium',
  targetUsage: 'websiteHero',
  camera: 'wideAngle',
  composition: 'ruleOfThirds',
  seed: '48291',
  variations: '4',
};

export const DEFAULT_SCORES: ImageScores = {
  overall: 92,
};

export const IB_PROJECTS: IbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Exterior Render',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Hero Visual',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Lifestyle Scene',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus 3224 Site Plan',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&h=900&q=85',
  },
];

export const DEFAULT_VARIATIONS: IbVariation[] = [
  {
    id: 'v1',
    label: 'A',
    thumbUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=400&h=225&q=80',
  },
  {
    id: 'v2',
    label: 'B',
    thumbUrl:
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=400&h=225&q=80',
  },
  {
    id: 'v3',
    label: 'C',
    thumbUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&h=225&q=80',
  },
  {
    id: 'v4',
    label: 'D',
    thumbUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=225&q=80',
  },
  {
    id: 'v5',
    label: 'E',
    thumbUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=400&h=225&q=80',
  },
];

export const COLLECTIONS = ['exteriorRenders', 'interiors', 'marketing', 'social'] as const;

export function getProject(id: ProjectId): IbProject {
  return IB_PROJECTS.find((p) => p.id === id) ?? IB_PROJECTS[0]!;
}

export function scoreTone(score: number): StatusChipTone {
  if (score >= 90) return 'success';
  if (score >= 75) return 'info';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function isFloorPlanType(type: GenerationType): boolean {
  return type === 'floorPlan';
}

export function isGeneralAiType(type: GenerationType): boolean {
  return type === 'generalAi';
}

export function aspectClass(ratio: AspectRatio): string {
  switch (ratio) {
    case '4:3':
      return 'is-43';
    case '1:1':
      return 'is-11';
    case '9:16':
      return 'is-916';
    case '3:4':
      return 'is-34';
    default:
      return 'is-169';
  }
}

export function aspectPixelSize(ratio: AspectRatio, longEdge: number): [number, number] {
  switch (ratio) {
    case '4:3':
      return [longEdge, Math.round((longEdge * 3) / 4)];
    case '1:1':
      return [longEdge, longEdge];
    case '9:16':
      return [Math.round((longEdge * 9) / 16), longEdge];
    case '3:4':
      return [Math.round((longEdge * 3) / 4), longEdge];
    default:
      return [longEdge, Math.round((longEdge * 9) / 16)];
  }
}

export function resolveOutputPixels(
  state: PrintExportState,
  aspect: AspectRatio,
  baseLongEdge = 2048,
): [number, number] {
  switch (state.resolution) {
    case '2048':
      return aspectPixelSize(aspect, 2048);
    case '4096':
      return aspectPixelSize(aspect, 4096);
    case '8192':
      return aspectPixelSize(aspect, 8192);
    case 'upscale2':
      return aspectPixelSize(aspect, baseLongEdge * 2);
    case 'upscale4':
      return aspectPixelSize(aspect, baseLongEdge * 4);
    case 'custom':
      return [Math.max(1, state.customWidth), Math.max(1, state.customHeight)];
    default:
      return aspectPixelSize(aspect, 4096);
  }
}

export function physicalInches(state: PrintExportState): [number, number] {
  if (state.preset !== 'custom') {
    return PRINT_PRESET_INCHES[state.preset];
  }
  const w = Math.max(0.1, state.physicalWidth);
  const h = Math.max(0.1, state.physicalHeight);
  if (state.unit === 'cm') return [w / 2.54, h / 2.54];
  if (state.unit === 'px') {
    const dpi = state.dpi === 'custom' ? state.customDpi : Number(state.dpi);
    return [w / Math.max(1, dpi), h / Math.max(1, dpi)];
  }
  return [w, h];
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function estimateExportBytes(
  width: number,
  height: number,
  format: PrintFormatKey | DigitalFormatKey,
  maxQuality: boolean,
): number {
  const pixels = width * height;
  const quality = maxQuality ? 1 : 0.72;
  switch (format) {
    case 'png':
      return Math.round(pixels * 3.2 * quality);
    case 'tiff':
      return Math.round(pixels * 6 * quality);
    case 'pdf':
      return Math.round(pixels * 2.4 * quality);
    case 'webp':
      return Math.round(pixels * 0.55 * quality);
    default:
      return Math.round(pixels * 0.85 * quality);
  }
}

export function evaluatePrintQuality(
  state: PrintExportState,
  aspect: AspectRatio,
): PrintValidation {
  const [pxW, pxH] = resolveOutputPixels(state, aspect);
  const [inW, inH] = physicalInches(state);
  const targetDpi = state.dpi === 'custom' ? state.customDpi : Number(state.dpi);
  const effectiveDpi = Math.min(pxW / inW, pxH / inH);
  const estimatedBytes = estimateExportBytes(
    pxW,
    pxH,
    state.path === 'print' ? state.printFormat : state.digitalFormat,
    state.maximumQuality,
  );

  const messages: PrintReadinessKey[] = [];
  let sharpness: PrintValidation['sharpness'] = 'excellent';
  let enlargementRisk: PrintValidation['enlargementRisk'] = 'low';

  if (effectiveDpi >= targetDpi * 0.95) {
    messages.push('readyToPrint');
    sharpness = 'excellent';
  } else if (effectiveDpi >= 200) {
    messages.push('needsUpscale');
    sharpness = 'good';
    enlargementRisk = 'medium';
  } else if (effectiveDpi >= 120) {
    messages.push('insufficientDpi');
    sharpness = 'fair';
    enlargementRisk = 'high';
  } else {
    messages.push('needsX4Upscale');
    sharpness = 'poor';
    enlargementRisk = 'high';
  }

  if (state.path === 'print' && state.colorProfile !== 'cmyk') {
    messages.push('cmykRecommended');
  }

  const bleedStatus: PrintValidation['bleedStatus'] =
    state.bleed === 'none' ? 'missing' : state.bleed === 'custom' ? 'custom' : 'ok';
  const safeAreaStatus: PrintValidation['safeAreaStatus'] = state.safeArea ? 'ok' : 'off';

  const needsAttention =
    effectiveDpi < targetDpi * 0.95 ||
    (state.path === 'print' && state.colorProfile !== 'cmyk') ||
    (state.path === 'print' && state.bleed === 'none');

  if (!needsAttention) {
    messages.unshift('printReady');
  } else {
    messages.unshift('needsAttention');
  }

  const unitLabel =
    state.unit === 'cm' ? 'cm' : state.unit === 'px' ? 'px' : 'in';
  let physW = inW;
  let physH = inH;
  if (state.unit === 'cm') {
    physW = inW * 2.54;
    physH = inH * 2.54;
  } else if (state.unit === 'px') {
    physW = pxW;
    physH = pxH;
  }

  return {
    effectiveDpi: Math.round(effectiveDpi),
    physicalLabel: `${physW.toFixed(state.unit === 'px' ? 0 : 2)} × ${physH.toFixed(state.unit === 'px' ? 0 : 2)} ${unitLabel}`,
    colorProfile: state.colorProfile,
    estimatedBytes,
    sharpness,
    enlargementRisk,
    bleedStatus,
    safeAreaStatus,
    messages,
    finalState: needsAttention ? 'needsAttention' : 'printReady',
  };
}

export function applyPrintPreset(preset: PrintPresetKey, prev: PrintExportState): PrintExportState {
  if (preset === 'custom') return { ...prev, preset };
  const [w, h] = PRINT_PRESET_INCHES[preset];
  return {
    ...prev,
    preset,
    unit: 'inch',
    physicalWidth: w,
    physicalHeight: h,
  };
}
