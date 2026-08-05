import type { IhIconName } from '@/components/icons/ih-icons';

export const AC_HOME = '/workspaces/creative-studio';
export const AI_CHAT_ROUTE = '/workspaces/creative-studio/ai-chat';

export type ModelId = 'investhome' | 'gpt4o' | 'claude' | 'gemini';

export type DetailTabId = 'templates' | 'assets' | 'outputs';

export type RailActionId =
  | 'score'
  | 'suggestions'
  | 'quickActions'
  | 'export'
  | 'history';

export type BottomActionKey =
  | 'addComponent'
  | 'text'
  | 'image'
  | 'video'
  | 'shape'
  | 'icon'
  | 'table'
  | 'chart'
  | 'timeline'
  | 'map'
  | 'button'
  | 'aiTool';

export type SortKey = 'newest' | 'oldest' | 'nameAsc';
export type ViewMode = 'thread' | 'compact';
export type SizePreset = 'small' | 'medium' | 'large';

export type ChatFolder = {
  id: string;
  name: string;
  count: number;
};

export type ChatThread = {
  id: string;
  title: string;
  preview: string;
  timeLabel: string;
  folderId: string;
  tags: string[];
  modelId: ModelId;
};

export type MessageRole = 'user' | 'assistant';

export type RichCard = {
  title: string;
  subtitle: string;
  imageUrl: string;
  primaryCta: string;
  secondaryCta: string;
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  richCard?: RichCard;
};

export type TemplateItem = {
  id: string;
  title: string;
  imageUrl: string;
};

export type AssetItem = {
  id: string;
  name: string;
  ext: string;
  thumbUrl?: string;
};

export type OutputItem = {
  id: string;
  title: string;
  type: string;
  timeLabel: string;
  icon: IhIconName;
};

export const MODELS: { id: ModelId; labelKey: string }[] = [
  { id: 'investhome', labelKey: 'investhome' },
  { id: 'gpt4o', labelKey: 'gpt4o' },
  { id: 'claude', labelKey: 'claude' },
  { id: 'gemini', labelKey: 'gemini' },
];

export const DETAIL_TABS: DetailTabId[] = ['templates', 'assets', 'outputs'];

export const RAIL_ACTIONS: { id: RailActionId; icon: IhIconName; labelKey: string }[] = [
  { id: 'score', icon: 'trendingUp', labelKey: 'score' },
  { id: 'suggestions', icon: 'sparkles', labelKey: 'suggestions' },
  { id: 'quickActions', icon: 'quickAction', labelKey: 'quickActions' },
  { id: 'export', icon: 'inbox', labelKey: 'export' },
  { id: 'history', icon: 'clock', labelKey: 'history' },
];

export const BOTTOM_ACTIONS: { key: BottomActionKey; icon: IhIconName }[] = [
  { key: 'addComponent', icon: 'plus' },
  { key: 'text', icon: 'documents' },
  { key: 'image', icon: 'inventory' },
  { key: 'video', icon: 'meeting' },
  { key: 'shape', icon: 'design' },
  { key: 'icon', icon: 'sparkles' },
  { key: 'table', icon: 'projects' },
  { key: 'chart', icon: 'barChart' },
  { key: 'timeline', icon: 'clock' },
  { key: 'map', icon: 'target' },
  { key: 'button', icon: 'quickAction' },
  { key: 'aiTool', icon: 'sparkles' },
];

export const STORAGE = {
  usedGb: 42.6,
  totalGb: 200,
  percent: 21,
} as const;

export const AI_USAGE = {
  percent: 21,
  usedLabel: '210',
  totalLabel: '1.000',
} as const;

export const FOLDERS: ChatFolder[] = [
  { id: 'favorites', name: 'Favori Sohbetler', count: 8 },
  { id: 'projects', name: 'Proje Bazlı', count: 14 },
  { id: 'marketing', name: 'Pazarlama Kampanyaları', count: 11 },
  { id: 'investor', name: 'Yatırımcı İçerikleri', count: 6 },
  { id: 'archive', name: 'Arşiv', count: 22 },
];

export const THREADS: ChatThread[] = [
  {
    id: 't1',
    title: 'Modern konut projesi landing page',
    preview: 'THE TEMPLE Residences hero ve CTA',
    timeLabel: '2 dk önce',
    folderId: 'projects',
    tags: ['Landing Page', 'Website Builder', 'Modern'],
    modelId: 'investhome',
  },
  {
    id: 't2',
    title: 'Lüks villa broşürü metinleri',
    preview: 'Kapak ve özellik blokları',
    timeLabel: '18 dk önce',
    folderId: 'marketing',
    tags: ['Brochure', 'Copy'],
    modelId: 'gpt4o',
  },
  {
    id: 't3',
    title: 'Yatırımcı sunum decki',
    preview: 'Q2 finansal özet slaytları',
    timeLabel: '1 sa önce',
    folderId: 'investor',
    tags: ['Presentation', 'Finance'],
    modelId: 'claude',
  },
  {
    id: 't4',
    title: 'Instagram reels senaryosu',
    preview: '15 sn lifestyle kesim',
    timeLabel: 'Dün',
    folderId: 'marketing',
    tags: ['Social', 'Video'],
    modelId: 'gemini',
  },
  {
    id: 't5',
    title: 'E-posta lansman serisi',
    preview: '3 adımlı nurture akışı',
    timeLabel: '2g önce',
    folderId: 'favorites',
    tags: ['Email', 'Campaign'],
    modelId: 'investhome',
  },
  {
    id: 't6',
    title: 'Satış ofisi kat planı özeti',
    preview: 'A1–A3 birim karşılaştırması',
    timeLabel: '3g önce',
    folderId: 'projects',
    tags: ['Sales', 'Floorplan'],
    modelId: 'gpt4o',
  },
];

const HERO =
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=960&h=540&q=80';
const TPL_A =
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=480&h=320&q=80';
const TPL_B =
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=480&h=320&q=80';
const ASSET_A =
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=240&h=180&q=80';
const ASSET_B =
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=240&h=180&q=80';

export const DEMO_MESSAGES: ChatMessage[] = [
  {
    id: 'm1',
    role: 'user',
    content:
      'THE TEMPLE Residences için modern bir landing page tasarla. Hero görseli, proje özeti, 3 özellik kartı ve yatırımcı CTA’sı olsun. Ton: premium, sakin, güven veren.',
  },
  {
    id: 'm2',
    role: 'assistant',
    content:
      'İşte THE TEMPLE Residences için premium bir landing page taslağı. Hero’da akşam cephe renderı, ardından kısa proje özeti ve yatırımcı odaklı CTA yer alıyor. İsterseniz metinleri veya renk paletini birlikte ince ayarlayabiliriz.',
    richCard: {
      title: 'THE TEMPLE RESIDENCES',
      subtitle: 'Premium living in the heart of the city',
      imageUrl: HERO,
      primaryCta: 'Detayları İncele',
      secondaryCta: 'Broşürü İndir',
    },
  },
];

export const SUGGESTIONS = ['titles', 'palette', 'cta', 'mobile'] as const;

export const TEMPLATES: TemplateItem[] = [
  { id: 'tpl1', title: 'Modern Landing Page', imageUrl: TPL_A },
  { id: 'tpl2', title: 'Yatırım Odaklı', imageUrl: TPL_B },
];

export const ASSETS: AssetItem[] = [
  { id: 'as1', name: 'temple-hero.jpg', ext: 'JPG', thumbUrl: ASSET_A },
  { id: 'as2', name: 'brand-logo.svg', ext: 'PNG', thumbUrl: ASSET_B },
  { id: 'as3', name: 'amenity-icon.svg', ext: 'SVG' },
  { id: 'as4', name: 'skyline.jpg', ext: 'JPG', thumbUrl: HERO },
];

export const OUTPUTS: OutputItem[] = [
  {
    id: 'o1',
    title: 'THE TEMPLE — Landing Page V1',
    type: 'HTML',
    timeLabel: '2 dk önce',
    icon: 'design',
  },
  {
    id: 'o2',
    title: 'Hero Copy — TR',
    type: 'TXT',
    timeLabel: '5 dk önce',
    icon: 'documents',
  },
  {
    id: 'o3',
    title: 'CTA Variant Set',
    type: 'DOC',
    timeLabel: '12 dk önce',
    icon: 'sparkles',
  },
];

export function filterThreads(
  threads: ChatThread[],
  opts: { query: string; folderId: string | null },
): ChatThread[] {
  const q = opts.query.trim().toLowerCase();
  return threads.filter((th) => {
    if (opts.folderId && th.folderId !== opts.folderId) return false;
    if (!q) return true;
    const hay = `${th.title} ${th.preview} ${th.tags.join(' ')}`.toLowerCase();
    return hay.includes(q);
  });
}
