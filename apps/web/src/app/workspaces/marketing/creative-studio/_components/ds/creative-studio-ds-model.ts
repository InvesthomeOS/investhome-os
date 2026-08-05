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
  | 'videoStudio'
  | 'imageStudio'
  | 'architecturalStudio'
  | 'emailStudio'
  | 'brochureCatalog'
  | 'aiChat'
  | 'templates'
  | 'mediaLibrary';

export type ContentStatus = 'draft' | 'generating' | 'published';

export type QuickActionKey = 'newProject' | 'generateAi' | 'uploadMedia' | 'fromTemplate';

export type SuggestionKey = 'templeWebsite' | 'instagram309' | 'investmentBrochure' | 'progressVideo';

export type SoftTint = 'cyan' | 'navy' | 'mint' | 'sky' | 'slate' | 'teal' | 'indigo' | 'foam';

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
};

export type ProjectItem = {
  id: string;
  name: string;
  thumbLabel: string;
  tint: SoftTint;
  assetCount: number;
  progress: number;
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

export type QuickActionItem = {
  key: QuickActionKey;
  href: string;
  icon: IhIconName;
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

export type CreativeStudioDsData = {
  kpis: KpiItem[];
  tools: ToolItem[];
  projects: ProjectItem[];
  recentContent: ContentItem[];
  quickActions: QuickActionItem[];
  activities: ActivityItem[];
  suggestions: SuggestionItem[];
};

export const CONTENT_STATUS_TONE: Record<ContentStatus, StatusChipTone> = {
  draft: 'default',
  generating: 'warning',
  published: 'success',
};

export const CREATIVE_STUDIO_FIXTURE: CreativeStudioDsData = {
  kpis: [
    { key: 'totalAssets', value: '248', delta: '+24', deltaTone: 'up', icon: 'documents' },
    { key: 'readyToPublish', value: '18', delta: '+6', deltaTone: 'up', icon: 'check' },
    { key: 'published', value: '132', delta: '+11', deltaTone: 'up', icon: 'trendingUp' },
    { key: 'aiJobs', value: '5', delta: '−2', deltaTone: 'down', icon: 'sparkles' },
    { key: 'imagesGenerated', value: '86', delta: '+19', deltaTone: 'up', icon: 'design' },
    { key: 'rendersGenerated', value: '27', delta: '+4', deltaTone: 'up', icon: 'projects' },
  ],
  tools: [
    {
      key: 'websiteBuilder',
      href: '/workspaces/marketing/landing-pages',
      icon: 'design',
      tint: 'navy',
    },
    {
      key: 'landingPages',
      href: '/workspaces/marketing/landing-pages',
      icon: 'target',
      tint: 'cyan',
    },
    {
      key: 'blogStudio',
      href: '/workspaces/marketing/content',
      icon: 'documents',
      tint: 'slate',
    },
    {
      key: 'socialStudio',
      href: '/workspaces/marketing/social',
      icon: 'activity',
      tint: 'sky',
    },
    {
      key: 'videoStudio',
      href: '/workspaces/marketing/content',
      icon: 'meeting',
      tint: 'indigo',
    },
    {
      key: 'imageStudio',
      href: '/workspaces/marketing/assets',
      icon: 'design',
      tint: 'teal',
    },
    {
      key: 'architecturalStudio',
      href: '/workspaces/marketing/brand',
      icon: 'projects',
      tint: 'navy',
    },
    {
      key: 'emailStudio',
      href: '/workspaces/marketing/email',
      icon: 'inbox',
      tint: 'mint',
    },
    {
      key: 'brochureCatalog',
      href: '/workspaces/marketing/assets',
      icon: 'documents',
      tint: 'foam',
    },
    {
      key: 'aiChat',
      href: '/workspaces/marketing/ai/assistant',
      icon: 'sparkles',
      tint: 'cyan',
    },
    {
      key: 'templates',
      href: '/workspaces/marketing/templates',
      icon: 'documents',
      tint: 'slate',
    },
    {
      key: 'mediaLibrary',
      href: '/workspaces/marketing/assets',
      icon: 'inventory',
      tint: 'teal',
    },
  ],
  projects: [
    {
      id: 'temple',
      name: 'THE TEMPLE Residences',
      thumbLabel: 'TT',
      tint: 'navy',
      assetCount: 12,
      progress: 78,
      updatedLabelKey: 'hours2',
      href: '/workspaces/marketing/content',
    },
    {
      id: '309h',
      name: '309 H ST NE',
      thumbLabel: '309',
      tint: 'cyan',
      assetCount: 9,
      progress: 54,
      updatedLabelKey: 'yesterday',
      href: '/workspaces/marketing/content',
    },
    {
      id: 'uniloft',
      name: 'UNILOFT DC',
      thumbLabel: 'UL',
      tint: 'teal',
      assetCount: 15,
      progress: 91,
      updatedLabelKey: 'days3',
      href: '/workspaces/marketing/content',
    },
    {
      id: 'campus',
      name: 'The Campus 3224',
      thumbLabel: 'TC',
      tint: 'slate',
      assetCount: 7,
      progress: 36,
      updatedLabelKey: 'week1',
      href: '/workspaces/marketing/content',
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
      href: '/workspaces/marketing/content',
    },
    {
      id: 'c2',
      titleKey: 'instagram',
      status: 'generating',
      updatedLabelKey: 'hours5',
      icon: 'activity',
      tint: 'cyan',
      href: '/workspaces/marketing/social',
    },
    {
      id: 'c3',
      titleKey: 'brochure',
      status: 'draft',
      updatedLabelKey: 'yesterday',
      icon: 'documents',
      tint: 'slate',
      href: '/workspaces/marketing/assets',
    },
    {
      id: 'c4',
      titleKey: 'video',
      status: 'generating',
      updatedLabelKey: 'days2',
      icon: 'meeting',
      tint: 'indigo',
      href: '/workspaces/marketing/content',
    },
    {
      id: 'c5',
      titleKey: 'blog',
      status: 'published',
      updatedLabelKey: 'days4',
      icon: 'documents',
      tint: 'mint',
      href: '/workspaces/marketing/content',
    },
  ],
  quickActions: [
    { key: 'newProject', href: '/workspaces/marketing/content/new', icon: 'plus' },
    { key: 'generateAi', href: '/workspaces/marketing/ai/assistant', icon: 'sparkles' },
    { key: 'uploadMedia', href: '/workspaces/marketing/assets', icon: 'inventory' },
    { key: 'fromTemplate', href: '/workspaces/marketing/templates', icon: 'documents' },
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
      href: '/workspaces/marketing/landing-pages',
      icon: 'design',
      tint: 'navy',
    },
    {
      key: 'instagram309',
      href: '/workspaces/marketing/social',
      icon: 'activity',
      tint: 'cyan',
    },
    {
      key: 'investmentBrochure',
      href: '/workspaces/marketing/assets',
      icon: 'documents',
      tint: 'teal',
    },
    {
      key: 'progressVideo',
      href: '/workspaces/marketing/content/new',
      icon: 'meeting',
      tint: 'indigo',
    },
  ],
};

export function buildCreativeStudioDsData(): CreativeStudioDsData {
  return CREATIVE_STUDIO_FIXTURE;
}
