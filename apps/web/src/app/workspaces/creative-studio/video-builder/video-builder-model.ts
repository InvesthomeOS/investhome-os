import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus = 'draft' | 'scheduled' | 'published' | 'archived';

export type CanvasTab = 'generate' | 'scenes' | 'edit' | 'brand' | 'audio' | 'subtitles';

export type AspectRatio = '16:9' | '9:16' | '1:1' | '4:5' | '21:9';

export type Resolution = '720' | '1080' | '4k';

export type Fps = '30' | '60';

export type SceneKind = 'hook' | 'project' | 'amenities' | 'drone' | 'investment' | 'cta';

export type LeftSectionKey = 'brief' | 'assets' | 'brand' | 'voiceMusic' | 'advanced';

export type AiActionKey =
  | 'completeVideo'
  | 'morePremium'
  | 'shorten'
  | 'investorVersion'
  | 'luxuryVersion'
  | 'socialVersion'
  | 'regenerateScene'
  | 'editScene'
  | 'replaceMedia'
  | 'makeCinematic'
  | 'makeLuxury'
  | 'lifestyleScene'
  | 'animatePhotos'
  | 'aiAvatar'
  | 'droneTransition'
  | 'instagramReel'
  | 'tiktokVersion'
  | 'youtubeVersion'
  | 'turkishVoice'
  | 'englishVoice';

export type AiStatusKey =
  | 'idle'
  | 'thinking'
  | 'summarizingBrief'
  | 'buildingStoryboard'
  | 'generatingScenes'
  | 'writingVoice'
  | 'optimizing'
  | 'completed';

export type AiProgressStepKey =
  | 'readingBrief'
  | 'analyzingAssets'
  | 'craftingScript'
  | 'buildingStoryboard'
  | 'generatingScenes'
  | 'scoringQuality'
  | 'readyToPublish';

export type SuggestionKey =
  | 'strongerHook'
  | 'betterCta'
  | 'improvePacing'
  | 'betterMusic'
  | 'shortenScene4'
  | 'moreLuxury';

export type QuickActionKey =
  | 'makeCinematic'
  | 'makeLuxury'
  | 'lifestyleScene'
  | 'animatePhotos'
  | 'aiAvatar'
  | 'droneTransition'
  | 'instagramReel'
  | 'tiktokVersion'
  | 'youtubeVersion'
  | 'turkishVoice'
  | 'englishVoice';

export type ExportOptionKey =
  | 'mp4'
  | '4k'
  | '1080p'
  | '16:9'
  | '9:16'
  | '1:1'
  | 'gif';

export type AssetCountKey = 'photos' | 'videos' | 'drone' | 'pdfs' | 'floorPlans' | 'logos';

export type VoiceKey = 'proMale' | 'proFemale' | 'narrator' | 'luxury' | 'tr' | 'en';

export type BrandKitKey = 'logo' | 'primaryColors' | 'typography' | 'introOutro' | 'watermark';

export type PreviewStatusChipKey = 'aiReady' | 'brandSafe' | 'subtitleReady' | 'voiceReady';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type VbChatMessage = {
  id: string;
  role: 'ai' | 'user';
  textKey?: 'welcome' | 'briefSummary' | 'generated' | 'refined' | 'ready';
  text?: string;
};

export type CampaignBrief = {
  videoType: string;
  project: string;
  audience: string;
  duration: string;
  language: string;
  tone: string;
  cta: string;
};

export type VideoScores = {
  overall: number;
  hookStrength: number;
  retention: number;
  cta: number;
  pacing: number;
};

export type SceneMetaKey =
  | 'voice'
  | 'subtitle'
  | 'music'
  | 'aiGenerated'
  | 'drone'
  | 'avatar'
  | 'animation';

export type ScoreFactorKey =
  | 'strongOpening'
  | 'brandConsistency'
  | 'goodPacing'
  | 'ctaImprove';

export type ScoreFactorTone = 'good' | 'warn';

export type AiSourceKey =
  | 'crm'
  | 'projectWorkspace'
  | 'websiteBuilder'
  | 'blogBuilder'
  | 'emailBuilder'
  | 'documents'
  | 'brandKit'
  | 'photos'
  | 'droneVideos'
  | 'floorPlans'
  | 'constructionGallery';

export type VbScene = {
  id: string;
  kind: SceneKind;
  durationSec: number;
  thumbUrl: string;
  meta?: SceneMetaKey[];
};

export type VbProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  featuredLabel: string;
  coverUrl: string;
};

export const VB_HOME = '/workspaces/creative-studio';
export const VB_ROUTE = '/workspaces/creative-studio/video-builder';

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  scheduled: 'info',
  published: 'success',
  archived: 'warning',
};

export const WORKFLOW_STEPS = ['brief', 'script', 'video', 'optimize', 'publish'] as const;

export const LEFT_SECTIONS: LeftSectionKey[] = [
  'brief',
  'assets',
  'brand',
  'voiceMusic',
  'advanced',
];

export const CANVAS_TABS: CanvasTab[] = [
  'generate',
  'scenes',
  'edit',
  'brand',
  'audio',
  'subtitles',
];

export const ASPECT_RATIOS: AspectRatio[] = ['16:9', '9:16', '1:1', '4:5'];

export const RESOLUTIONS: Resolution[] = ['720', '1080', '4k'];

export const FPS_OPTIONS: Fps[] = ['30', '60'];

export const PREVIEW_STATUS_CHIPS: PreviewStatusChipKey[] = [
  'aiReady',
  'brandSafe',
  'subtitleReady',
  'voiceReady',
];

export const AI_STATUS_SEQUENCE: AiStatusKey[] = [
  'thinking',
  'summarizingBrief',
  'buildingStoryboard',
  'generatingScenes',
  'writingVoice',
  'optimizing',
  'completed',
];

export const AI_PROGRESS_STEPS: AiProgressStepKey[] = [
  'readingBrief',
  'analyzingAssets',
  'craftingScript',
  'buildingStoryboard',
  'generatingScenes',
  'scoringQuality',
  'readyToPublish',
];

export const AI_SUGGESTIONS: SuggestionKey[] = [
  'strongerHook',
  'betterCta',
  'improvePacing',
  'betterMusic',
  'shortenScene4',
  'moreLuxury',
];

export const QUICK_ACTIONS: { key: QuickActionKey; icon: IhIconName }[] = [
  { key: 'makeCinematic', icon: 'meeting' },
  { key: 'makeLuxury', icon: 'sparkles' },
  { key: 'lifestyleScene', icon: 'design' },
  { key: 'animatePhotos', icon: 'activity' },
  { key: 'aiAvatar', icon: 'users' },
  { key: 'droneTransition', icon: 'trendingUp' },
  { key: 'instagramReel', icon: 'activity' },
  { key: 'tiktokVersion', icon: 'trendingUp' },
  { key: 'youtubeVersion', icon: 'meeting' },
  { key: 'turkishVoice', icon: 'users' },
  { key: 'englishVoice', icon: 'users' },
];

export const EXPORT_OPTIONS: ExportOptionKey[] = [
  'mp4',
  '4k',
  '1080p',
  '16:9',
  '9:16',
  '1:1',
  'gif',
];

export const EXPORT_FORMAT_OPTIONS: ExportOptionKey[] = ['mp4', '4k', '1080p'];
export const EXPORT_RATIO_OPTIONS: ExportOptionKey[] = ['16:9', '9:16', '1:1'];

export const AI_SOURCES: AiSourceKey[] = [
  'crm',
  'projectWorkspace',
  'websiteBuilder',
  'blogBuilder',
  'emailBuilder',
  'documents',
  'brandKit',
  'photos',
  'droneVideos',
  'floorPlans',
  'constructionGallery',
];

export const SCORE_FACTORS: { key: ScoreFactorKey; tone: ScoreFactorTone }[] = [
  { key: 'strongOpening', tone: 'good' },
  { key: 'brandConsistency', tone: 'good' },
  { key: 'goodPacing', tone: 'good' },
  { key: 'ctaImprove', tone: 'warn' },
];

export const SCENE_META_ICON: Record<SceneMetaKey, IhIconName> = {
  voice: 'users',
  subtitle: 'documents',
  music: 'activity',
  aiGenerated: 'sparkles',
  drone: 'trendingUp',
  avatar: 'user',
  animation: 'design',
};

export const ASSET_COUNTS: { key: AssetCountKey; count: number }[] = [
  { key: 'photos', count: 34 },
  { key: 'videos', count: 8 },
  { key: 'drone', count: 2 },
  { key: 'pdfs', count: 5 },
  { key: 'floorPlans', count: 12 },
  { key: 'logos', count: 3 },
];

export const BRAND_KIT: BrandKitKey[] = [
  'logo',
  'primaryColors',
  'typography',
  'introOutro',
  'watermark',
];

export const VOICES: VoiceKey[] = ['proMale', 'proFemale', 'narrator', 'luxury', 'tr', 'en'];

export const MUSIC_STYLES = ['ambient', 'cinematic', 'luxury', 'uplift'] as const;

export const DEFAULT_BRIEF: CampaignBrief = {
  videoType: 'Investment promo',
  project: 'THE TEMPLE Residences',
  audience: 'Investors & brokers',
  duration: '45s',
  language: 'EN / TR',
  tone: 'Premium, reassuring',
  cta: 'Discover investment opportunity',
};

export const DEFAULT_SCORES: VideoScores = {
  overall: 92,
  hookStrength: 91,
  retention: 88,
  cta: 94,
  pacing: 90,
};

export const VB_PROJECTS: VbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Launch',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Investor Update',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Early Access',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=1600&h=900&q=85',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus 3224 Preview',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1600&h=900&q=85',
  },
];

export const DEFAULT_SCENES: VbScene[] = [
  {
    id: 'sc-1',
    kind: 'hook',
    durationSec: 6,
    thumbUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=400&h=225&q=80',
    meta: ['voice', 'subtitle', 'aiGenerated'],
  },
  {
    id: 'sc-2',
    kind: 'project',
    durationSec: 10,
    thumbUrl:
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=400&h=225&q=80',
    meta: ['voice', 'music', 'animation'],
  },
  {
    id: 'sc-3',
    kind: 'amenities',
    durationSec: 8,
    thumbUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=225&q=80',
    meta: ['subtitle', 'music', 'aiGenerated'],
  },
  {
    id: 'sc-4',
    kind: 'drone',
    durationSec: 8,
    thumbUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&h=225&q=80',
    meta: ['drone', 'music', 'aiGenerated'],
  },
  {
    id: 'sc-5',
    kind: 'investment',
    durationSec: 8,
    thumbUrl:
      'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=400&h=225&q=80',
    meta: ['voice', 'subtitle', 'avatar'],
  },
  {
    id: 'sc-6',
    kind: 'cta',
    durationSec: 5,
    thumbUrl:
      'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=400&h=225&q=80',
    meta: ['voice', 'subtitle', 'music'],
  },
];

export const VB_CHAT: VbChatMessage[] = [{ id: 'c1', role: 'ai', textKey: 'welcome' }];

export function getProject(id: ProjectId): VbProject {
  return VB_PROJECTS.find((p) => p.id === id) ?? VB_PROJECTS[0]!;
}

export function scoreTone(score: number): StatusChipTone {
  if (score >= 90) return 'success';
  if (score >= 75) return 'info';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function formatTimecode(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function totalDuration(scenes: VbScene[]): number {
  return scenes.reduce((sum, s) => sum + s.durationSec, 0);
}
