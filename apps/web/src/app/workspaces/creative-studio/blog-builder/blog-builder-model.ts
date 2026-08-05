import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type PublishStatus = 'draft' | 'scheduled' | 'published' | 'archived';

export type BbLeftRailId = 'components' | 'templates' | 'styles' | 'settings';
export type BbRightRailId = 'post' | 'style' | 'seo';

export type DevicePreview = 'desktop' | 'tablet' | 'mobile';

export type BottomActionKey =
  | 'addSection'
  | 'text'
  | 'image'
  | 'gallery'
  | 'video'
  | 'quote'
  | 'list'
  | 'table'
  | 'code'
  | 'divider'
  | 'other';

export type ComponentGroupKey = 'basic' | 'content' | 'postElements';

export type ComponentItemKey =
  | 'heading'
  | 'text'
  | 'image'
  | 'video'
  | 'button'
  | 'divider'
  | 'quote'
  | 'list'
  | 'table'
  | 'toc'
  | 'codeBlock'
  | 'embed'
  | 'authorBox'
  | 'publishDate'
  | 'tags'
  | 'share'
  | 'relatedPosts'
  | 'comments';

export type PageKind =
  | 'home'
  | 'postList'
  | 'postDetail'
  | 'category'
  | 'authors'
  | 'search'
  | 'custom';

export type SectionKey =
  | 'header'
  | 'meta'
  | 'title'
  | 'lead'
  | 'cover'
  | 'body'
  | 'quote'
  | 'cta'
  | 'faq'
  | 'related';

export type SectionTrayActionKey =
  | 'edit'
  | 'duplicate'
  | 'delete'
  | 'moveUp'
  | 'moveDown'
  | 'settings';

export type ArticleTemplateKey =
  | 'investmentGuide'
  | 'marketUpdate'
  | 'projectDeepDive'
  | 'faqExplainer'
  | 'buyerJourney';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type BbPage = {
  id: string;
  kind: PageKind;
  thumbUrl: string;
};

export type BbSection = {
  id: string;
  key: SectionKey;
  label: string;
};

export type BbTemplate = {
  id: string;
  type: ArticleTemplateKey;
  tint: string;
};

export type BbProject = {
  id: ProjectId;
  name: string;
  slug: string;
  featuredLabel: string;
  coverUrl: string;
};

export type SeoScores = {
  overall: number;
  keywordUsage: number;
  readability: number;
};

export const BB_HOME = '/workspaces/creative-studio';
export const BB_ROUTE = '/workspaces/creative-studio/blog-builder';

export const PUBLISH_STATUS_TONE: Record<PublishStatus, StatusChipTone> = {
  draft: 'default',
  scheduled: 'info',
  published: 'success',
  archived: 'warning',
};

export const DEVICE_TOGGLE: DevicePreview[] = ['desktop', 'tablet', 'mobile'];

export const DEVICE_CONTENT: Record<DevicePreview, { w: number; h: number }> = {
  desktop: { w: 820, h: 1200 },
  tablet: { w: 768, h: 1024 },
  mobile: { w: 390, h: 844 },
};

export const BB_LEFT_RAIL_IDS: BbLeftRailId[] = [
  'components',
  'templates',
  'styles',
  'settings',
];

export const BB_LEFT_RAIL_ICONS: Record<BbLeftRailId, IhIconName> = {
  components: 'documents',
  templates: 'inventory',
  styles: 'settings',
  settings: 'sparkles',
};

export const BB_RIGHT_RAIL_IDS: BbRightRailId[] = ['post', 'style', 'seo'];

export const BB_RIGHT_RAIL_ICONS: Record<BbRightRailId, IhIconName> = {
  post: 'documents',
  style: 'design',
  seo: 'search',
};

export const BB_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addSection', icon: 'plus' },
  { key: 'text', icon: 'documents' },
  { key: 'image', icon: 'inventory' },
  { key: 'gallery', icon: 'design' },
  { key: 'video', icon: 'meeting' },
  { key: 'quote', icon: 'inbox' },
  { key: 'list', icon: 'documents' },
  { key: 'table', icon: 'inventory' },
  { key: 'code', icon: 'executive' },
  { key: 'divider', icon: 'activity' },
  { key: 'other', icon: 'quickAction' },
];

export const COMPONENT_LIBRARY: {
  group: ComponentGroupKey;
  items: { key: ComponentItemKey; icon: IhIconName }[];
}[] = [
  {
    group: 'basic',
    items: [
      { key: 'heading', icon: 'marketing' },
      { key: 'text', icon: 'documents' },
      { key: 'image', icon: 'inventory' },
      { key: 'video', icon: 'meeting' },
      { key: 'button', icon: 'quickAction' },
      { key: 'divider', icon: 'activity' },
    ],
  },
  {
    group: 'content',
    items: [
      { key: 'quote', icon: 'inbox' },
      { key: 'list', icon: 'documents' },
      { key: 'table', icon: 'inventory' },
      { key: 'toc', icon: 'design' },
      { key: 'codeBlock', icon: 'executive' },
      { key: 'embed', icon: 'activity' },
    ],
  },
  {
    group: 'postElements',
    items: [
      { key: 'authorBox', icon: 'users' },
      { key: 'publishDate', icon: 'clock' },
      { key: 'tags', icon: 'target' },
      { key: 'share', icon: 'activity' },
      { key: 'relatedPosts', icon: 'documents' },
      { key: 'comments', icon: 'inbox' },
    ],
  },
];

export const STYLE_PRESETS = [
  { id: 'navy', labelKey: 'navy', swatch: '#075b75' },
  { id: 'slate', labelKey: 'slate', swatch: '#1e2b33' },
  { id: 'sand', labelKey: 'sand', swatch: '#c4b49a' },
] as const;

export const CATEGORIES = ['Investment Guide', 'Market Update', 'Project Spotlight', 'Buyer Tips'] as const;

export const DEFAULT_TAGS = ['gayrimenkul', 'yatırım', 'washington-dc'] as const;

const PAGE_THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=400&h=260&q=80',
];

export const DEFAULT_PAGES: BbPage[] = [
  { id: 'pg-home', kind: 'home', thumbUrl: PAGE_THUMBS[0]! },
  { id: 'pg-list', kind: 'postList', thumbUrl: PAGE_THUMBS[1]! },
  { id: 'pg-detail', kind: 'postDetail', thumbUrl: PAGE_THUMBS[2]! },
  { id: 'pg-category', kind: 'category', thumbUrl: PAGE_THUMBS[3]! },
  { id: 'pg-authors', kind: 'authors', thumbUrl: PAGE_THUMBS[4]! },
  { id: 'pg-search', kind: 'search', thumbUrl: PAGE_THUMBS[5]! },
];

export const DEFAULT_SECTIONS: BbSection[] = [
  { id: 's-header', key: 'header', label: 'Header' },
  { id: 's-meta', key: 'meta', label: 'Meta' },
  { id: 's-title', key: 'title', label: 'Title' },
  { id: 's-lead', key: 'lead', label: 'Lead' },
  { id: 's-cover', key: 'cover', label: 'Cover' },
  { id: 's-body', key: 'body', label: 'Body' },
  { id: 's-quote', key: 'quote', label: 'Quote' },
  { id: 's-cta', key: 'cta', label: 'CTA' },
  { id: 's-faq', key: 'faq', label: 'FAQ' },
];

export const BB_TEMPLATES: BbTemplate[] = [
  { id: 't1', type: 'investmentGuide', tint: '#eef6f8' },
  { id: 't2', type: 'marketUpdate', tint: '#f0f7f4' },
  { id: 't3', type: 'projectDeepDive', tint: '#f3f6fb' },
  { id: 't4', type: 'faqExplainer', tint: '#f7fafb' },
  { id: 't5', type: 'buyerJourney', tint: '#eef8fa' },
];

export const BB_PROJECTS: BbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    slug: 'washington-dc-investment-guide',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1617581629397-a725307f3f5d?auto=format&fit=crop&w=1600&h=900&q=80',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    slug: '309-h-st-investment-guide',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=80',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    slug: 'uniloft-dc-guide',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1600&h=900&q=80',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    slug: 'campus-3224-guide',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1600&h=900&q=80',
  },
];

export const FAQ_KEYS = ['whyDc', 'bestNeighborhoods', 'entryBudget', 'timeline'] as const;

export const FEATURE_GRID_KEYS = [
  'strongDemand',
  'rentalPotential',
  'capitalGrowth',
  'stableMarket',
] as const;

export const INLINE_IMAGE_URL =
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&h=700&q=80';

export const DEFAULT_SEO: SeoScores = {
  overall: 92,
  keywordUsage: 94,
  readability: 93,
};

export function getProject(id: ProjectId): BbProject {
  return BB_PROJECTS.find((p) => p.id === id) ?? BB_PROJECTS[0]!;
}

export function scoreTone(score: number): StatusChipTone {
  if (score >= 90) return 'success';
  if (score >= 75) return 'info';
  if (score >= 60) return 'warning';
  return 'danger';
}

export function reorderPages(pages: BbPage[], fromId: string, toId: string): BbPage[] {
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
