import type { IhIconName } from '@/components/icons/ih-icons';
import type { StatusChipTone } from '@investhome/ui';

export type CampaignStatus = 'draft' | 'ready' | 'exported' | 'published' | 'archived';

export type ProjectId = 'temple' | '309h' | 'uniloft' | 'campus';

export type PageStatus = 'ready' | 'draft' | 'review';

export type SpreadMode = 'single' | 'spread';

export type BrbLeftRailId =
  | 'pages'
  | 'templates'
  | 'sections'
  | 'assets'
  | 'texts'
  | 'brand'
  | 'settings';

export type BrbRightRailId = 'design' | 'page' | 'interaction' | 'notes';

export type BottomActionKey =
  | 'addComponent'
  | 'heading'
  | 'text'
  | 'image'
  | 'gallery'
  | 'icon'
  | 'divider'
  | 'table'
  | 'chart'
  | 'timeline'
  | 'map'
  | 'video'
  | 'button'
  | 'quote'
  | 'other';

export type FloatingActionKey = 'edit' | 'copy' | 'delete' | 'layer' | 'align';

export type PageKind =
  | 'cover'
  | 'execSummary'
  | 'location'
  | 'amenities'
  | 'floorPlans'
  | 'investment'
  | 'financials'
  | 'lifestyle'
  | 'gallery'
  | 'timeline'
  | 'team'
  | 'contact';

export type BgMode = 'color' | 'image' | 'gradient';

export type MarginPreset = 'compact' | 'normal' | 'wide';

export type BrochurePage = {
  id: string;
  kind: PageKind;
  name: string;
  thumbUrl: string;
  status: PageStatus;
};

export type BrochureProject = {
  id: ProjectId;
  name: string;
  campaignName: string;
  coverUrl: string;
};

export type BrochureTemplate = {
  id: string;
  category: 'investor' | 'sales' | 'lifestyle' | 'minimal';
  thumbUrl: string;
};

export const BRB_HOME = '/workspaces/creative-studio';
export const BRB_ROUTE = '/workspaces/creative-studio/brochure-builder';

/** A4 @ 96dpi */
export const A4_WIDTH = 794;
export const A4_HEIGHT = 1123;

export const CAMPAIGN_STATUS_TONE: Record<CampaignStatus, StatusChipTone> = {
  draft: 'default',
  ready: 'success',
  exported: 'info',
  published: 'success',
  archived: 'warning',
};

export const PAGE_STATUS_TONE: Record<PageStatus, StatusChipTone> = {
  ready: 'success',
  draft: 'default',
  review: 'warning',
};

export const BRB_LEFT_RAIL_IDS: BrbLeftRailId[] = [
  'pages',
  'templates',
  'sections',
  'assets',
  'texts',
  'brand',
  'settings',
];

export const BRB_LEFT_RAIL_ICONS: Record<BrbLeftRailId, IhIconName> = {
  pages: 'documents',
  templates: 'inventory',
  sections: 'projects',
  assets: 'theme',
  texts: 'marketing',
  brand: 'sparkles',
  settings: 'settings',
};

export const BRB_RIGHT_RAIL_IDS: BrbRightRailId[] = [
  'design',
  'page',
  'interaction',
  'notes',
];

export const BRB_RIGHT_RAIL_ICONS: Record<BrbRightRailId, IhIconName> = {
  design: 'design',
  page: 'documents',
  interaction: 'activity',
  notes: 'marketing',
};

export const BRB_ZOOM_PRESETS = [25, 50, 75, 100, 125, 150, 200] as const;

export const FLOATING_ACTIONS: { key: FloatingActionKey; icon: IhIconName }[] = [
  { key: 'edit', icon: 'design' },
  { key: 'copy', icon: 'documents' },
  { key: 'delete', icon: 'activity' },
  { key: 'layer', icon: 'inventory' },
  { key: 'align', icon: 'target' },
];

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addComponent', icon: 'plus' },
  { key: 'heading', icon: 'marketing' },
  { key: 'text', icon: 'documents' },
  { key: 'image', icon: 'inventory' },
  { key: 'gallery', icon: 'theme' },
  { key: 'icon', icon: 'sparkles' },
  { key: 'divider', icon: 'activity' },
  { key: 'table', icon: 'projects' },
  { key: 'chart', icon: 'barChart' },
  { key: 'timeline', icon: 'clock' },
  { key: 'map', icon: 'target' },
  { key: 'video', icon: 'meeting' },
  { key: 'button', icon: 'quickAction' },
  { key: 'quote', icon: 'sparkles' },
  { key: 'other', icon: 'quickAction' },
];

export const SECTION_KINDS: { kind: PageKind; icon: IhIconName }[] = [
  { kind: 'cover', icon: 'documents' },
  { kind: 'execSummary', icon: 'sparkles' },
  { kind: 'location', icon: 'target' },
  { kind: 'amenities', icon: 'activity' },
  { kind: 'floorPlans', icon: 'projects' },
  { kind: 'investment', icon: 'trendingUp' },
  { kind: 'financials', icon: 'barChart' },
  { kind: 'lifestyle', icon: 'theme' },
  { kind: 'gallery', icon: 'inventory' },
  { kind: 'timeline', icon: 'clock' },
  { kind: 'team', icon: 'users' },
  { kind: 'contact', icon: 'marketing' },
];

export const BRAND_COLORS = ['#075B75', '#58AEBB', '#1E2B33', '#C4A574', '#FFFFFF'] as const;

export const FONT_OPTIONS = ['Inter Display', 'Source Serif', 'Manrope', 'DM Sans'] as const;

export const MARGIN_PRESETS: MarginPreset[] = ['compact', 'normal', 'wide'];

const THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=720&h=1020&q=80',
  'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?auto=format&fit=crop&w=720&h=1020&q=80',
];

export const BRB_PROJECTS: BrochureProject[] = [
  {
    id: 'temple',
    name: 'THE TEMPLE Residences',
    campaignName: 'THE TEMPLE Investor Brochure',
    coverUrl: THUMBS[0]!,
  },
  {
    id: '309h',
    name: '309 H ST NE',
    campaignName: '309 H ST Sales Brochure',
    coverUrl: THUMBS[1]!,
  },
  {
    id: 'uniloft',
    name: 'UNILOFT DC',
    campaignName: 'UNILOFT Lifestyle Brochure',
    coverUrl: THUMBS[2]!,
  },
  {
    id: 'campus',
    name: 'The Campus 3224',
    campaignName: 'Campus 3224 Brochure',
    coverUrl: THUMBS[3]!,
  },
];

export const BRB_TEMPLATES: BrochureTemplate[] = [
  { id: 't1', category: 'investor', thumbUrl: THUMBS[0]! },
  { id: 't2', category: 'sales', thumbUrl: THUMBS[1]! },
  { id: 't3', category: 'lifestyle', thumbUrl: THUMBS[2]! },
  { id: 't4', category: 'minimal', thumbUrl: THUMBS[3]! },
  { id: 't5', category: 'investor', thumbUrl: THUMBS[4]! },
  { id: 't6', category: 'sales', thumbUrl: THUMBS[5]! },
];

const DEFAULT_PAGE_KINDS: PageKind[] = [
  'cover',
  'execSummary',
  'location',
  'amenities',
  'floorPlans',
  'investment',
  'financials',
  'lifestyle',
  'gallery',
  'timeline',
  'team',
  'contact',
];

const DEFAULT_PAGE_NAMES: Record<PageKind, string> = {
  cover: 'Kapak',
  execSummary: 'Yatırım Özeti',
  location: 'Lokasyon',
  amenities: 'Olanaklar',
  floorPlans: 'Kat Planları',
  investment: 'Yatırım Fırsatı',
  financials: 'Finansallar',
  lifestyle: 'Yaşam',
  gallery: 'Galeri',
  timeline: 'Zaman Çizelgesi',
  team: 'Ekip',
  contact: 'İletişim',
};

export const DEFAULT_PAGES: BrochurePage[] = DEFAULT_PAGE_KINDS.map((kind, index) => ({
  id: `pg-${index + 1}`,
  kind,
  name: DEFAULT_PAGE_NAMES[kind],
  thumbUrl: THUMBS[index % THUMBS.length]!,
  status: index < 8 ? 'ready' : index < 10 ? 'review' : 'draft',
}));

export function getProject(id: ProjectId): BrochureProject {
  return BRB_PROJECTS.find((p) => p.id === id) ?? BRB_PROJECTS[0]!;
}

export function createPage(index: number, thumbUrl: string): BrochurePage {
  return {
    id: `pg-${Date.now()}`,
    kind: 'gallery',
    name: `Sayfa ${index}`,
    thumbUrl,
    status: 'draft',
  };
}

export function resolveSpreadSize(mode: SpreadMode): { w: number; h: number } {
  if (mode === 'spread') return { w: A4_WIDTH * 2, h: A4_HEIGHT };
  return { w: A4_WIDTH, h: A4_HEIGHT };
}

export function spreadPartnerIndex(index: number, total: number): number | null {
  if (total < 2) return null;
  if (index % 2 === 0) {
    return index + 1 < total ? index + 1 : null;
  }
  return index - 1;
}
