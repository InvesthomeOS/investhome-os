import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type PublishStatus = 'draft' | 'scheduled' | 'published' | 'archived';

export type EbLeftRailId = 'components' | 'templates' | 'styles' | 'settings';
export type EbRightRailId = 'content' | 'style' | 'settings';

export type DevicePreview = 'desktop' | 'tablet' | 'mobile';

export type BottomActionKey =
  | 'addSection'
  | 'text'
  | 'image'
  | 'gallery'
  | 'button'
  | 'video'
  | 'divider'
  | 'social'
  | 'html'
  | 'counter'
  | 'table'
  | 'iconText'
  | 'other';

export type ComponentGroupKey = 'basic' | 'layout' | 'content' | 'advanced';

export type ComponentItemKey =
  | 'title'
  | 'text'
  | 'image'
  | 'button'
  | 'divider'
  | 'social'
  | 'cols1'
  | 'cols2'
  | 'cols3'
  | 'cols21'
  | 'cols12'
  | 'card'
  | 'video'
  | 'iconText'
  | 'counter'
  | 'quote'
  | 'list'
  | 'table'
  | 'html'
  | 'previewText'
  | 'spacer';

export type SectionKey =
  | 'header'
  | 'hero'
  | 'features'
  | 'cta'
  | 'gallery'
  | 'blog'
  | 'footer'
  | 'divider'
  | 'spacer'
  | 'html'
  | 'social';

export type SectionTrayActionKey =
  | 'edit'
  | 'duplicate'
  | 'delete'
  | 'moveUp'
  | 'moveDown'
  | 'settings';

export type EmailTemplateKey =
  | 'newsletter'
  | 'productLaunch'
  | 'invitation'
  | 'digest'
  | 'announcement';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type EbSection = {
  id: string;
  key: SectionKey;
  label: string;
  thumbUrl: string;
};

export type EbTemplate = {
  id: string;
  type: EmailTemplateKey;
  tint: string;
};

export type EbProject = {
  id: ProjectId;
  name: string;
  slug: string;
  featuredLabel: string;
  coverUrl: string;
};

export const EB_HOME = '/workspaces/creative-studio';
export const EB_ROUTE = '/workspaces/creative-studio/email-builder';

export const PUBLISH_STATUS_TONE: Record<PublishStatus, StatusChipTone> = {
  draft: 'default',
  scheduled: 'info',
  published: 'success',
  archived: 'warning',
};

export const DEVICE_TOGGLE: DevicePreview[] = ['desktop', 'tablet', 'mobile'];

/** Email-oriented canvas sizes (desktop uses classic ~600px email width). */
export const DEVICE_CONTENT: Record<DevicePreview, { w: number; h: number }> = {
  desktop: { w: 600, h: 900 },
  tablet: { w: 768, h: 1024 },
  mobile: { w: 390, h: 844 },
};

export const EB_LEFT_RAIL_IDS: EbLeftRailId[] = [
  'components',
  'templates',
  'styles',
  'settings',
];

export const EB_LEFT_RAIL_ICONS: Record<EbLeftRailId, IhIconName> = {
  components: 'documents',
  templates: 'inventory',
  styles: 'settings',
  settings: 'sparkles',
};

export const EB_RIGHT_RAIL_IDS: EbRightRailId[] = ['content', 'style', 'settings'];

export const EB_RIGHT_RAIL_ICONS: Record<EbRightRailId, IhIconName> = {
  content: 'documents',
  style: 'design',
  settings: 'settings',
};

export const EB_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addSection', icon: 'plus' },
  { key: 'text', icon: 'documents' },
  { key: 'image', icon: 'inventory' },
  { key: 'gallery', icon: 'design' },
  { key: 'button', icon: 'quickAction' },
  { key: 'video', icon: 'meeting' },
  { key: 'divider', icon: 'activity' },
  { key: 'social', icon: 'users' },
  { key: 'html', icon: 'executive' },
  { key: 'counter', icon: 'barChart' },
  { key: 'table', icon: 'inventory' },
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
      { key: 'divider', icon: 'activity' },
      { key: 'social', icon: 'users' },
    ],
  },
  {
    group: 'layout',
    items: [
      { key: 'cols1', icon: 'documents' },
      { key: 'cols2', icon: 'design' },
      { key: 'cols3', icon: 'inventory' },
      { key: 'cols21', icon: 'activity' },
      { key: 'cols12', icon: 'executive' },
      { key: 'card', icon: 'inbox' },
    ],
  },
  {
    group: 'content',
    items: [
      { key: 'video', icon: 'meeting' },
      { key: 'iconText', icon: 'marketing' },
      { key: 'counter', icon: 'barChart' },
      { key: 'quote', icon: 'inbox' },
      { key: 'list', icon: 'documents' },
      { key: 'table', icon: 'inventory' },
    ],
  },
  {
    group: 'advanced',
    items: [
      { key: 'html', icon: 'executive' },
      { key: 'previewText', icon: 'documents' },
      { key: 'spacer', icon: 'activity' },
    ],
  },
];

export const STYLE_PRESETS = [
  { id: 'navy', labelKey: 'navy', swatch: '#075b75' },
  { id: 'slate', labelKey: 'slate', swatch: '#1e2b33' },
  { id: 'sand', labelKey: 'sand', swatch: '#c4b49a' },
] as const;

const SECTION_THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=400&h=260&q=80',
  'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=400&h=260&q=80',
];

export const DEFAULT_SECTIONS: EbSection[] = [
  { id: 's-header', key: 'header', label: 'Header', thumbUrl: SECTION_THUMBS[0]! },
  { id: 's-hero', key: 'hero', label: 'Hero', thumbUrl: SECTION_THUMBS[1]! },
  { id: 's-features', key: 'features', label: 'Features', thumbUrl: SECTION_THUMBS[2]! },
  { id: 's-cta', key: 'cta', label: 'CTA', thumbUrl: SECTION_THUMBS[3]! },
  { id: 's-gallery', key: 'gallery', label: 'Gallery', thumbUrl: SECTION_THUMBS[4]! },
  { id: 's-blog', key: 'blog', label: 'Blog', thumbUrl: SECTION_THUMBS[5]! },
  { id: 's-footer', key: 'footer', label: 'Footer', thumbUrl: SECTION_THUMBS[6]! },
];

export const EB_TEMPLATES: EbTemplate[] = [
  { id: 't1', type: 'newsletter', tint: '#eef6f8' },
  { id: 't2', type: 'productLaunch', tint: '#f0f7f4' },
  { id: 't3', type: 'invitation', tint: '#f3f6fb' },
  { id: 't4', type: 'digest', tint: '#f7fafb' },
  { id: 't5', type: 'announcement', tint: '#eef8fa' },
];

export const EB_PROJECTS: EbProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    slug: 'the-temple-launch',
    featuredLabel: 'THE TEMPLE',
    coverUrl:
      'https://images.unsplash.com/photo-1617581629397-a725307f3f5d?auto=format&fit=crop&w=1600&h=900&q=80',
  },
  {
    id: '309h',
    name: '309 H ST NE',
    slug: '309-h-st-update',
    featuredLabel: '309 H ST NE',
    coverUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1600&h=900&q=80',
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    slug: 'uniloft-early-access',
    featuredLabel: 'UNILOFT',
    coverUrl:
      'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=1600&h=900&q=80',
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    slug: 'campus-3224-preview',
    featuredLabel: 'CAMPUS 3224',
    coverUrl:
      'https://images.unsplash.com/photo-1460317442991-0ec209397118?auto=format&fit=crop&w=1600&h=900&q=80',
  },
];

export const FEATURE_GRID_KEYS = ['location', 'design', 'returns'] as const;

export const SOCIAL_LINK_KEYS = ['linkedin', 'x', 'instagram', 'youtube'] as const;

export const GALLERY_IMAGE_URLS = [
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=400&h=280&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=400&h=280&q=80',
  'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?auto=format&fit=crop&w=400&h=280&q=80',
] as const;

export const RELATED_POST_KEYS = ['guide', 'market', 'spotlight'] as const;

export const LINK_TYPE_KEYS = ['url', 'email', 'phone', 'unsubscribe'] as const;

export function getProject(id: ProjectId): EbProject {
  return EB_PROJECTS.find((p) => p.id === id) ?? EB_PROJECTS[0]!;
}

export function reorderSections(
  sections: EbSection[],
  fromId: string,
  toId: string,
): EbSection[] {
  if (fromId === toId) return sections;
  const fromIndex = sections.findIndex((s) => s.id === fromId);
  const toIndex = sections.findIndex((s) => s.id === toId);
  if (fromIndex < 0 || toIndex < 0) return sections;
  const next = [...sections];
  const [moved] = next.splice(fromIndex, 1);
  if (!moved) return sections;
  next.splice(toIndex, 0, moved);
  return next;
}
