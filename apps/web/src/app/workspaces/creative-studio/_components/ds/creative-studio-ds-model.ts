import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type KpiKey =
  | 'totalAssets'
  | 'readyToPublish'
  | 'published'
  | 'aiJobs'
  | 'imagesGenerated'
  | 'rendersGenerated';

export type ToolKey =
  | 'websiteBuilder'
  | 'landingPages'
  | 'blogStudio'
  | 'socialStudio'
  | 'adsBuilder'
  | 'videoStudio'
  | 'imageStudio'
  | 'architecturalStudio'
  | 'emailStudio'
  | 'brochureStudio'
  | 'presentationStudio'
  | 'proposalStudio'
  | 'templates'
  | 'mediaLibrary'
  | 'aiChat';

export type HeroShortcutKey =
  | 'website'
  | 'blog'
  | 'instagram'
  | 'video'
  | 'brochure'
  | 'render3d'
  | 'presentation'
  | 'proposal';

export type ContentStatus = 'draft' | 'generating' | 'published';

export type SuggestionKey =
  | 'templeWebsite'
  | 'instagram309'
  | 'investmentBrochure'
  | 'progressVideo'
  | 'investorPresentation';

export type SoftTint = 'cyan' | 'navy' | 'mint' | 'sky' | 'slate' | 'teal' | 'indigo' | 'foam';

export type JobStatus = 'running' | 'pending' | 'failed' | 'continue';

export type KpiItem = {
  key: KpiKey;
  value: string;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
  icon: IhIconName;
};

export type ToolItem = {
  key: ToolKey;
  href: string;
  icon: IhIconName;
  tint: SoftTint;
  workflowSteps: string[];
  drafts: number;
  lastProductionKey: 'hours2' | 'hours5' | 'yesterday' | 'days2' | 'days3' | 'week1';
  runningJobs: number;
};

export type HeroShortcut = {
  key: HeroShortcutKey;
  toolKey: ToolKey;
  icon: IhIconName;
  tint: SoftTint;
};

export type ProjectItem = {
  id: string;
  name: string;
  thumbLabel: string;
  thumbUrl?: string;
  tint: SoftTint;
  assetCount: number;
  progress: number;
  jobsRunning: number;
  updatedLabelKey: 'hours2' | 'yesterday' | 'days3' | 'week1';
  href: string;
};

export type ContentItem = {
  id: string;
  titleKey: 'homepage' | 'instagram' | 'brochure' | 'video' | 'blog';
  status: ContentStatus;
  updatedLabelKey: 'hours1' | 'hours5' | 'yesterday' | 'days2' | 'days4';
  icon: IhIconName;
  tint: SoftTint;
  href: string;
};

export type ActivityItem = {
  id: string;
  initials: string;
  tone: SoftTint;
  nameKey: 'ayse' | 'mehmet' | 'selin' | 'can';
  actionKey: 'publishedHomepage' | 'generatedRender' | 'uploadedMedia' | 'startedAiJob';
  timeLabelKey: 'mins12' | 'hours1' | 'hours3' | 'yesterday';
};

export type SuggestionItem = {
  key: SuggestionKey;
  href: string;
  icon: IhIconName;
  tint: SoftTint;
};

export type RailJobItem = {
  id: string;
  status: JobStatus;
  titleKey: string;
  metaKey: string;
  href: string;
  icon: IhIconName;
  tint: SoftTint;
};

export type CreativeStudioDsData = {
  kpis: KpiItem[];
  heroShortcuts: HeroShortcut[];
  tools: ToolItem[];
  projects: ProjectItem[];
  recentContent: ContentItem[];
  activities: ActivityItem[];
  suggestions: SuggestionItem[];
  railJobs: RailJobItem[];
};

export const CONTENT_STATUS_TONE: Record<ContentStatus, StatusChipTone> = {
  draft: 'default',
  generating: 'warning',
  published: 'success',
};

export const JOB_STATUS_TONE: Record<JobStatus, StatusChipTone> = {
  running: 'info',
  pending: 'warning',
  failed: 'danger',
  continue: 'default',
};

export const WEBSITE_BUILDER_ROUTE = '/workspaces/creative-studio/website-builder';
export const LANDING_PAGE_BUILDER_ROUTE = '/workspaces/creative-studio/landing-page-builder';
export const BLOG_BUILDER_ROUTE = '/workspaces/creative-studio/blog-builder';
export const EMAIL_BUILDER_ROUTE = '/workspaces/creative-studio/email-builder';
export const VIDEO_BUILDER_ROUTE = '/workspaces/creative-studio/video-builder';
export const IMAGE_BUILDER_ROUTE = '/workspaces/creative-studio/image-builder';
export const PRESENTATION_BUILDER_ROUTE = '/workspaces/creative-studio/presentation-builder';
export const PROPOSAL_BUILDER_ROUTE = '/workspaces/creative-studio/proposal-builder';
export const SOCIAL_MEDIA_BUILDER_ROUTE = '/workspaces/creative-studio/social-media-builder';
export const QUICK_CREATIVE_ROUTE = '/workspaces/creative-studio/hizli-tasarim';
export const PREMIUM_CAMPAIGNS_ROUTE = '/workspaces/creative-studio/premium-campaigns';
/** Phase 13.0 FINAL — HUMAN_APPROVED production lock. Do not redesign this workspace. */
export const PREMIUM_CAMPAIGN_PRODUCTION_LOCK = {
  status: 'PRODUCTION_READY',
  ui: 'HUMAN_APPROVED',
  routing: 'ACTIVE',
  familyId: 'd0e00220-5f9b-530a-847d-17c1f82bbad9',
  route: `${PREMIUM_CAMPAIGNS_ROUTE}/d0e00220-5f9b-530a-847d-17c1f82bbad9`,
  next: 'AI QUICK CREATIVE — LIVE PROJECT WORKFLOW',
} as const;
export const ADS_BUILDER_ROUTE = '/workspaces/creative-studio/ads-builder';
export const BROCHURE_BUILDER_ROUTE = '/workspaces/creative-studio/brochure-builder';
export const MEDIA_LIBRARY_ROUTE = '/workspaces/creative-studio/media-library';
export const AI_CHAT_ROUTE = '/workspaces/creative-studio/ai-chat';
export const TEMPLATES_ROUTE = '/workspaces/creative-studio/templates';
export const ARCHITECTURAL_STUDIO_ROUTE =
  '/workspaces/creative-studio/architectural-studio';

export const toolHref = (tool: ToolKey) => {
  if (tool === 'websiteBuilder') return WEBSITE_BUILDER_ROUTE;
  if (tool === 'landingPages') return LANDING_PAGE_BUILDER_ROUTE;
  if (tool === 'blogStudio') return BLOG_BUILDER_ROUTE;
  if (tool === 'socialStudio') return QUICK_CREATIVE_ROUTE;
  if (tool === 'adsBuilder') return ADS_BUILDER_ROUTE;
  if (tool === 'emailStudio') return EMAIL_BUILDER_ROUTE;
  if (tool === 'videoStudio') return VIDEO_BUILDER_ROUTE;
  if (tool === 'imageStudio') return IMAGE_BUILDER_ROUTE;
  if (tool === 'presentationStudio') return PRESENTATION_BUILDER_ROUTE;
  if (tool === 'proposalStudio') return PROPOSAL_BUILDER_ROUTE;
  if (tool === 'brochureStudio') return BROCHURE_BUILDER_ROUTE;
  if (tool === 'architecturalStudio') return ARCHITECTURAL_STUDIO_ROUTE;
  if (tool === 'templates') return TEMPLATES_ROUTE;
  if (tool === 'mediaLibrary') return MEDIA_LIBRARY_ROUTE;
  if (tool === 'aiChat') return AI_CHAT_ROUTE;
  return `/workspaces/creative-studio/produce/${tool}`;
};

const produce = toolHref;

/** Short QA aliases → canonical ToolKey */
export const TOOL_ALIASES: Record<string, ToolKey> = {
  website: 'websiteBuilder',
  blog: 'blogStudio',
  'blog-builder': 'blogStudio',
  blogBuilder: 'blogStudio',
  'blog-studio': 'blogStudio',
  social: 'socialStudio',
  'social-media': 'socialStudio',
  'social-media-builder': 'socialStudio',
  socialMedia: 'socialStudio',
  socialMediaBuilder: 'socialStudio',
  'social-studio': 'socialStudio',
  socialstudio: 'socialStudio',
  ads: 'adsBuilder',
  'ads-builder': 'adsBuilder',
  adsBuilder: 'adsBuilder',
  'ads-studio': 'adsBuilder',
  adsStudio: 'adsBuilder',
  video: 'videoStudio',
  'video-builder': 'videoStudio',
  videoBuilder: 'videoStudio',
  'video-studio': 'videoStudio',
  image: 'imageStudio',
  'image-builder': 'imageStudio',
  imageBuilder: 'imageStudio',
  'image-studio': 'imageStudio',
  architectural: 'architecturalStudio',
  'architectural-studio': 'architecturalStudio',
  architecturalStudio: 'architecturalStudio',
  websiteBuilder: 'websiteBuilder',
  landingPages: 'landingPages',
  landing: 'landingPages',
  'landing-page': 'landingPages',
  'landing-pages': 'landingPages',
  landingPageBuilder: 'landingPages',
  blogStudio: 'blogStudio',
  socialStudio: 'socialStudio',
  adsBuilder: 'adsBuilder',
  videoStudio: 'videoStudio',
  imageStudio: 'imageStudio',
  emailStudio: 'emailStudio',
  email: 'emailStudio',
  'email-builder': 'emailStudio',
  emailBuilder: 'emailStudio',
  'email-studio': 'emailStudio',
  brochureStudio: 'brochureStudio',
  brochure: 'brochureStudio',
  'brochure-builder': 'brochureStudio',
  brochureBuilder: 'brochureStudio',
  'brochure-studio': 'brochureStudio',
  presentationStudio: 'presentationStudio',
  presentation: 'presentationStudio',
  'presentation-builder': 'presentationStudio',
  presentationBuilder: 'presentationStudio',
  'presentation-studio': 'presentationStudio',
  presentationstudio: 'presentationStudio',
  proposalStudio: 'proposalStudio',
  proposal: 'proposalStudio',
  'proposal-builder': 'proposalStudio',
  proposalBuilder: 'proposalStudio',
  'proposal-studio': 'proposalStudio',
  proposalstudio: 'proposalStudio',
  templates: 'templates',
  template: 'templates',
  sablonlar: 'templates',
  'template-library': 'templates',
  templateLibrary: 'templates',
  mediaLibrary: 'mediaLibrary',
  'media-library': 'mediaLibrary',
  media: 'mediaLibrary',
  medya: 'mediaLibrary',
  aiChat: 'aiChat',
  'ai-chat': 'aiChat',
  chat: 'aiChat',
  chatBuilder: 'aiChat',
  'chat-builder': 'aiChat',
  'ai-chat-builder': 'aiChat',
};

export const TOOL_WORKFLOWS: Record<ToolKey, string[]> = {
  websiteBuilder: ['project', 'websiteType', 'language', 'generate'],
  landingPages: ['project', 'campaign', 'language', 'generate'],
  blogStudio: ['project', 'seo', 'tone', 'generate'],
  socialStudio: ['brief', 'platforms', 'contentIdeas', 'design', 'textTags', 'scheduleExport'],
  adsBuilder: ['brief', 'platforms', 'design', 'export'],
  videoStudio: ['brief', 'script', 'video', 'optimize', 'publish'],
  imageStudio: ['brief', 'styleRef', 'generate', 'edit', 'export'],
  architecturalStudio: ['uploadPlan', 'analyze', 'model3d', 'render', 'video'],
  emailStudio: ['brief', 'design', 'review', 'send'],
  brochureStudio: ['project', 'audience', 'language', 'generate'],
  presentationStudio: ['brief', 'outline', 'design', 'content', 'preview'],
  proposalStudio: ['brief', 'content', 'design', 'review', 'preview'],
  templates: ['category', 'brand', 'customize', 'use'],
  mediaLibrary: ['browse', 'filter', 'select', 'use'],
  aiChat: ['brief', 'iterate', 'refine', 'export'],
};

function tool(
  key: ToolKey,
  icon: IhIconName,
  tint: SoftTint,
  drafts: number,
  lastProductionKey: ToolItem['lastProductionKey'],
  runningJobs: number,
): ToolItem {
  return {
    key,
    href: produce(key),
    icon,
    tint,
    workflowSteps: TOOL_WORKFLOWS[key],
    drafts,
    lastProductionKey,
    runningJobs,
  };
}

export const CREATIVE_STUDIO_FIXTURE: CreativeStudioDsData = {
  kpis: [
    { key: 'totalAssets', value: '248', delta: '+24', deltaTone: 'up', icon: 'documents' },
    { key: 'readyToPublish', value: '18', delta: '+6', deltaTone: 'up', icon: 'check' },
    { key: 'published', value: '132', delta: '+11', deltaTone: 'up', icon: 'trendingUp' },
    { key: 'aiJobs', value: '5', delta: '−2', deltaTone: 'down', icon: 'sparkles' },
    { key: 'imagesGenerated', value: '86', delta: '+19', deltaTone: 'up', icon: 'design' },
    { key: 'rendersGenerated', value: '27', delta: '+4', deltaTone: 'up', icon: 'projects' },
  ],
  heroShortcuts: [
    { key: 'website', toolKey: 'websiteBuilder', icon: 'design', tint: 'navy' },
    { key: 'blog', toolKey: 'blogStudio', icon: 'documents', tint: 'mint' },
    { key: 'instagram', toolKey: 'socialStudio', icon: 'activity', tint: 'sky' },
    { key: 'video', toolKey: 'videoStudio', icon: 'meeting', tint: 'indigo' },
    { key: 'brochure', toolKey: 'brochureStudio', icon: 'documents', tint: 'foam' },
    { key: 'render3d', toolKey: 'architecturalStudio', icon: 'projects', tint: 'teal' },
    { key: 'presentation', toolKey: 'presentationStudio', icon: 'target', tint: 'slate' },
    { key: 'proposal', toolKey: 'proposalStudio', icon: 'documents', tint: 'navy' },
  ],
  tools: [
    tool('websiteBuilder', 'design', 'navy', 3, 'hours2', 1),
    tool('landingPages', 'target', 'cyan', 2, 'hours5', 0),
    tool('blogStudio', 'documents', 'mint', 4, 'yesterday', 0),
    tool('socialStudio', 'activity', 'sky', 5, 'hours2', 1),
    tool('adsBuilder', 'trendingUp', 'cyan', 3, 'hours5', 0),
    tool('videoStudio', 'meeting', 'indigo', 1, 'days2', 1),
    tool('imageStudio', 'design', 'teal', 6, 'hours5', 0),
    tool('architecturalStudio', 'projects', 'navy', 2, 'yesterday', 1),
    tool('emailStudio', 'inbox', 'mint', 3, 'days3', 0),
    tool('brochureStudio', 'documents', 'foam', 2, 'hours2', 0),
    tool('presentationStudio', 'target', 'slate', 2, 'hours2', 0),
    tool('proposalStudio', 'documents', 'navy', 2, 'hours2', 0),
    tool('templates', 'documents', 'slate', 0, 'week1', 0),
    tool('mediaLibrary', 'inventory', 'teal', 0, 'hours5', 0),
    tool('aiChat', 'sparkles', 'cyan', 1, 'hours2', 0),
  ],
  projects: [
    {
      id: 'temple',
      name: 'THE TEMPLE Residences',
      thumbLabel: 'TT',
      thumbUrl:
        'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=160&h=160&q=80',
      tint: 'navy',
      assetCount: 12,
      progress: 78,
      jobsRunning: 2,
      updatedLabelKey: 'hours2',
      href: produce('websiteBuilder'),
    },
    {
      id: '309h',
      name: '309 H ST NE',
      thumbLabel: '309',
      thumbUrl:
        'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=160&h=160&q=80',
      tint: 'cyan',
      assetCount: 9,
      progress: 54,
      jobsRunning: 1,
      updatedLabelKey: 'yesterday',
      href: produce('socialStudio'),
    },
    {
      id: 'uniloft',
      name: 'UNILOFT DC',
      thumbLabel: 'UL',
      thumbUrl:
        'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=160&h=160&q=80',
      tint: 'teal',
      assetCount: 15,
      progress: 91,
      jobsRunning: 0,
      updatedLabelKey: 'days3',
      href: produce('brochureStudio'),
    },
    {
      id: 'campus',
      name: 'The Campus 3224',
      thumbLabel: 'TC',
      thumbUrl:
        'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=160&h=160&q=80',
      tint: 'slate',
      assetCount: 7,
      progress: 36,
      jobsRunning: 1,
      updatedLabelKey: 'week1',
      href: produce('architecturalStudio'),
    },
  ],
  recentContent: [
    {
      id: 'c1',
      titleKey: 'homepage',
      status: 'published',
      updatedLabelKey: 'hours1',
      icon: 'design',
      tint: 'navy',
      href: produce('websiteBuilder'),
    },
    {
      id: 'c2',
      titleKey: 'instagram',
      status: 'generating',
      updatedLabelKey: 'hours5',
      icon: 'activity',
      tint: 'cyan',
      href: produce('socialStudio'),
    },
    {
      id: 'c3',
      titleKey: 'brochure',
      status: 'draft',
      updatedLabelKey: 'yesterday',
      icon: 'documents',
      tint: 'slate',
      href: produce('brochureStudio'),
    },
    {
      id: 'c4',
      titleKey: 'video',
      status: 'generating',
      updatedLabelKey: 'days2',
      icon: 'meeting',
      tint: 'indigo',
      href: produce('videoStudio'),
    },
    {
      id: 'c5',
      titleKey: 'blog',
      status: 'published',
      updatedLabelKey: 'days4',
      icon: 'documents',
      tint: 'mint',
      href: produce('blogStudio'),
    },
  ],
  activities: [
    {
      id: 'a1',
      initials: 'AY',
      tone: 'navy',
      nameKey: 'ayse',
      actionKey: 'publishedHomepage',
      timeLabelKey: 'mins12',
    },
    {
      id: 'a2',
      initials: 'MK',
      tone: 'cyan',
      nameKey: 'mehmet',
      actionKey: 'generatedRender',
      timeLabelKey: 'hours1',
    },
    {
      id: 'a3',
      initials: 'SD',
      tone: 'teal',
      nameKey: 'selin',
      actionKey: 'uploadedMedia',
      timeLabelKey: 'hours3',
    },
    {
      id: 'a4',
      initials: 'CY',
      tone: 'slate',
      nameKey: 'can',
      actionKey: 'startedAiJob',
      timeLabelKey: 'yesterday',
    },
  ],
  suggestions: [
    {
      key: 'templeWebsite',
      href: produce('websiteBuilder'),
      icon: 'design',
      tint: 'navy',
    },
    {
      key: 'instagram309',
      href: produce('socialStudio'),
      icon: 'activity',
      tint: 'cyan',
    },
    {
      key: 'investmentBrochure',
      href: produce('brochureStudio'),
      icon: 'documents',
      tint: 'teal',
    },
    {
      key: 'progressVideo',
      href: produce('videoStudio'),
      icon: 'meeting',
      tint: 'indigo',
    },
    {
      key: 'investorPresentation',
      href: produce('presentationStudio'),
      icon: 'target',
      tint: 'slate',
    },
  ],
  railJobs: [
    {
      id: 'j1',
      status: 'running',
      titleKey: 'templeHomepage',
      metaKey: 'eta4',
      href: produce('websiteBuilder'),
      icon: 'design',
      tint: 'navy',
    },
    {
      id: 'j2',
      status: 'running',
      titleKey: 'renderCampus',
      metaKey: 'eta12',
      href: produce('architecturalStudio'),
      icon: 'projects',
      tint: 'teal',
    },
    {
      id: 'j3',
      status: 'pending',
      titleKey: 'instagramApproval',
      metaKey: 'awaitingReview',
      href: produce('socialStudio'),
      icon: 'activity',
      tint: 'sky',
    },
    {
      id: 'j4',
      status: 'failed',
      titleKey: 'videoExport',
      metaKey: 'retryNeeded',
      href: produce('videoStudio'),
      icon: 'meeting',
      tint: 'indigo',
    },
    {
      id: 'j5',
      status: 'continue',
      titleKey: 'brochureDraft',
      metaKey: 'hours2',
      href: produce('brochureStudio'),
      icon: 'documents',
      tint: 'foam',
    },
  ],
};

export function resolveToolKey(value: string): ToolKey | null {
  return TOOL_ALIASES[value] ?? null;
}

export function isToolKey(value: string): value is ToolKey {
  return value in TOOL_WORKFLOWS;
}

export function buildCreativeStudioDsData(): CreativeStudioDsData {
  return CREATIVE_STUDIO_FIXTURE;
}
