import type { IhIconName } from '@/components/icons/ih-icons';

export const ML_HOME = '/workspaces/creative-studio';

export type AssetKind =
  | 'image'
  | 'video'
  | 'document'
  | 'audio'
  | 'template'
  | 'brand'
  | 'other';

export type FileExt = 'JPG' | 'PNG' | 'SVG' | 'MP4' | 'PDF' | 'PPTX' | 'DOCX' | 'MP3' | 'WAV';

export type SidebarTypeId =
  | 'all'
  | 'images'
  | 'videos'
  | 'documents'
  | 'audio'
  | 'templates'
  | 'brand'
  | 'favorites'
  | 'trash';

export type CenterTabId = 'all' | 'images' | 'videos' | 'documents' | 'audio' | 'other';

export type DetailTabId = 'details' | 'tags' | 'history' | 'usage';

export type QuickActionId = 'info' | 'tag' | 'link' | 'share' | 'download' | 'delete';

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
  | 'quote'
  | 'other';

export type ViewMode = 'grid' | 'list';
export type SortKey = 'newest' | 'oldest' | 'nameAsc' | 'sizeDesc';
export type SizePreset = 'small' | 'medium' | 'large';

export type MediaFolder = {
  id: string;
  name: string;
  count: number;
  children?: MediaFolder[];
};

export type AssetUsage = {
  id: string;
  tool: string;
  label: string;
  icon: IhIconName;
};

export type AssetHistory = {
  id: string;
  action: string;
  actor: string;
  at: string;
};

export type MediaAsset = {
  id: string;
  name: string;
  kind: AssetKind;
  ext: FileExt;
  sizeLabel: string;
  sizeBytes: number;
  dateLabel: string;
  addedAt: string;
  addedBy: string;
  folderId: string;
  folderName: string;
  favorite: boolean;
  trashed: boolean;
  thumbUrl?: string;
  resolution?: string;
  duration?: string;
  description: string;
  tags: string[];
  usages: AssetUsage[];
  history: AssetHistory[];
};

export const SIDEBAR_TYPES: { id: SidebarTypeId; icon: IhIconName }[] = [
  { id: 'all', icon: 'inventory' },
  { id: 'images', icon: 'design' },
  { id: 'videos', icon: 'meeting' },
  { id: 'documents', icon: 'documents' },
  { id: 'audio', icon: 'activity' },
  { id: 'templates', icon: 'theme' },
  { id: 'brand', icon: 'sparkles' },
  { id: 'favorites', icon: 'check' },
  { id: 'trash', icon: 'alert' },
];

export const CENTER_TABS: { id: CenterTabId; icon: IhIconName }[] = [
  { id: 'all', icon: 'inventory' },
  { id: 'images', icon: 'design' },
  { id: 'videos', icon: 'meeting' },
  { id: 'documents', icon: 'documents' },
  { id: 'audio', icon: 'activity' },
  { id: 'other', icon: 'quickAction' },
];

export const DETAIL_TABS: DetailTabId[] = ['details', 'tags', 'history', 'usage'];

export const QUICK_ACTIONS: { id: QuickActionId; icon: IhIconName }[] = [
  { id: 'info', icon: 'alert' },
  { id: 'tag', icon: 'sparkles' },
  { id: 'link', icon: 'arrowRight' },
  { id: 'share', icon: 'users' },
  { id: 'download', icon: 'inbox' },
  { id: 'delete', icon: 'activity' },
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
  { key: 'quote', icon: 'marketing' },
  { key: 'other', icon: 'chevronDown' },
];

export const STORAGE = {
  usedGb: 42.6,
  totalGb: 200,
  percent: 21,
} as const;

export const FOLDERS: MediaFolder[] = [
  { id: 'temple', name: 'THE TEMPLE Residences', count: 245 },
  { id: 'social', name: 'Sosyal Medya', count: 312 },
  { id: 'brand', name: 'Marka Kitleri', count: 86 },
  { id: 'renders', name: '3B Renderlar', count: 154 },
  {
    id: 'campaigns',
    name: 'Kampanyalar',
    count: 98,
    children: [
      { id: 'campaigns-q2', name: '2026 Q2', count: 42 },
      { id: 'campaigns-launch', name: 'Lansman', count: 56 },
    ],
  },
  { id: 'documents', name: 'Belgeler', count: 67 },
];

const USAGE_WB: AssetUsage = {
  id: 'u1',
  tool: 'Website Builder',
  label: 'Ana Sayfa',
  icon: 'design',
};
const USAGE_SMB: AssetUsage = {
  id: 'u2',
  tool: 'Social Media Builder',
  label: 'Instagram Post',
  icon: 'activity',
};
const USAGE_BRB: AssetUsage = {
  id: 'u3',
  tool: 'Brochure Studio',
  label: 'Kapak',
  icon: 'documents',
};
const USAGE_PB: AssetUsage = {
  id: 'u4',
  tool: 'Presentation Builder',
  label: 'Slayt 3',
  icon: 'target',
};

function hist(id: string, action: string, actor: string, at: string): AssetHistory {
  return { id, action, actor, at };
}

const THUMBS = [
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=640&h=480&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=640&h=480&q=80',
];

export const DEMO_ASSETS: MediaAsset[] = [
  {
    id: 'a1',
    name: 'the-temple-exterior.jpg',
    kind: 'image',
    ext: 'JPG',
    sizeLabel: '2.4 MB',
    sizeBytes: 2_400_000,
    dateLabel: '2 dk önce',
    addedAt: '4 Ağustos 2026, 16:42',
    addedBy: 'Ayşe Demir',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: true,
    trashed: false,
    thumbUrl: THUMBS[0],
    resolution: '3840×2160',
    description: 'THE TEMPLE Residences dış cephe akşam renderı — ana hero görseli.',
    tags: ['dış cephe', 'bina', 'render', 'hero'],
    usages: [USAGE_WB, USAGE_BRB],
    history: [
      hist('h1', 'Yüklendi', 'Ayşe Demir', '4 Ağu 2026, 16:42'),
      hist('h2', 'Etiketler güncellendi', 'Ayşe Demir', '4 Ağu 2026, 16:44'),
      hist('h3', 'Website Builder’da kullanıldı', 'Mehmet Kaya', '4 Ağu 2026, 16:50'),
    ],
  },
  {
    id: 'a2',
    name: 'lobby-interior.png',
    kind: 'image',
    ext: 'PNG',
    sizeLabel: '4.1 MB',
    sizeBytes: 4_100_000,
    dateLabel: '18 dk önce',
    addedAt: '4 Ağustos 2026, 16:26',
    addedBy: 'Selin Arslan',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: false,
    trashed: false,
    thumbUrl: THUMBS[1],
    resolution: '2560×1440',
    description: 'Lobi iç mekan — soft lighting varyasyon.',
    tags: ['iç mekan', 'lobi', 'lifestyle'],
    usages: [USAGE_PB],
    history: [hist('h1', 'Yüklendi', 'Selin Arslan', '4 Ağu 2026, 16:26')],
  },
  {
    id: 'a3',
    name: 'drone-flythrough.mp4',
    kind: 'video',
    ext: 'MP4',
    sizeLabel: '86.2 MB',
    sizeBytes: 86_200_000,
    dateLabel: '1 sa önce',
    addedAt: '4 Ağustos 2026, 15:40',
    addedBy: 'Can Yıldız',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: true,
    trashed: false,
    thumbUrl: THUMBS[2],
    duration: '01:24',
    resolution: '1920×1080',
    description: 'Drone flythrough — şantiye ve çevre.',
    tags: ['drone', 'video', 'şantiye'],
    usages: [USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Can Yıldız', '4 Ağu 2026, 15:40')],
  },
  {
    id: 'a4',
    name: 'investment-deck.pdf',
    kind: 'document',
    ext: 'PDF',
    sizeLabel: '12.8 MB',
    sizeBytes: 12_800_000,
    dateLabel: '3 sa önce',
    addedAt: '4 Ağustos 2026, 13:20',
    addedBy: 'Mehmet Kaya',
    folderId: 'documents',
    folderName: 'Belgeler',
    favorite: false,
    trashed: false,
    description: 'Yatırımcı sunum PDF — Q2 özeti.',
    tags: ['yatırımcı', 'pdf', 'finans'],
    usages: [USAGE_PB, USAGE_BRB],
    history: [hist('h1', 'Yüklendi', 'Mehmet Kaya', '4 Ağu 2026, 13:20')],
  },
  {
    id: 'a5',
    name: 'amenity-pool.jpg',
    kind: 'image',
    ext: 'JPG',
    sizeLabel: '3.2 MB',
    sizeBytes: 3_200_000,
    dateLabel: 'Dün',
    addedAt: '3 Ağustos 2026, 11:05',
    addedBy: 'Ayşe Demir',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: false,
    trashed: false,
    thumbUrl: THUMBS[3],
    resolution: '4000×2667',
    description: 'Havuz ve sosyal alan renderı.',
    tags: ['havuz', 'amenity', 'lifestyle'],
    usages: [USAGE_WB, USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Ayşe Demir', '3 Ağu 2026, 11:05')],
  },
  {
    id: 'a6',
    name: 'brand-logo.svg',
    kind: 'brand',
    ext: 'SVG',
    sizeLabel: '48 KB',
    sizeBytes: 48_000,
    dateLabel: '2g önce',
    addedAt: '2 Ağustos 2026, 09:12',
    addedBy: 'Selin Arslan',
    folderId: 'brand',
    folderName: 'Marka Kitleri',
    favorite: true,
    trashed: false,
    description: 'Investhome ana logo — vektör.',
    tags: ['logo', 'marka', 'svg'],
    usages: [USAGE_WB, USAGE_BRB, USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Selin Arslan', '2 Ağu 2026, 09:12')],
  },
  {
    id: 'a7',
    name: 'social-carousel-01.png',
    kind: 'image',
    ext: 'PNG',
    sizeLabel: '1.8 MB',
    sizeBytes: 1_800_000,
    dateLabel: '2g önce',
    addedAt: '2 Ağustos 2026, 14:30',
    addedBy: 'Can Yıldız',
    folderId: 'social',
    folderName: 'Sosyal Medya',
    favorite: false,
    trashed: false,
    thumbUrl: THUMBS[4],
    resolution: '1080×1080',
    description: 'Instagram carousel kare 1.',
    tags: ['sosyal', 'instagram', 'carousel'],
    usages: [USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Can Yıldız', '2 Ağu 2026, 14:30')],
  },
  {
    id: 'a8',
    name: 'unit-mix.pptx',
    kind: 'document',
    ext: 'PPTX',
    sizeLabel: '9.4 MB',
    sizeBytes: 9_400_000,
    dateLabel: '3g önce',
    addedAt: '1 Ağustos 2026, 16:00',
    addedBy: 'Mehmet Kaya',
    folderId: 'documents',
    folderName: 'Belgeler',
    favorite: false,
    trashed: false,
    description: 'Ünite karışımı sunumu.',
    tags: ['satış', 'ünite', 'pptx'],
    usages: [USAGE_PB],
    history: [hist('h1', 'Yüklendi', 'Mehmet Kaya', '1 Ağu 2026, 16:00')],
  },
  {
    id: 'a9',
    name: 'skyline-dusk.jpg',
    kind: 'image',
    ext: 'JPG',
    sizeLabel: '5.6 MB',
    sizeBytes: 5_600_000,
    dateLabel: '4g önce',
    addedAt: '31 Temmuz 2026, 19:22',
    addedBy: 'Ayşe Demir',
    folderId: 'renders',
    folderName: '3B Renderlar',
    favorite: true,
    trashed: false,
    thumbUrl: THUMBS[5],
    resolution: '5120×2880',
    description: 'Şehir silüeti akşam ışığı.',
    tags: ['skyline', 'render', 'dusk'],
    usages: [USAGE_WB],
    history: [hist('h1', 'Yüklendi', 'Ayşe Demir', '31 Tem 2026, 19:22')],
  },
  {
    id: 'a10',
    name: 'voiceover-tr.mp3',
    kind: 'audio',
    ext: 'MP3',
    sizeLabel: '6.1 MB',
    sizeBytes: 6_100_000,
    dateLabel: '5g önce',
    addedAt: '30 Temmuz 2026, 10:15',
    addedBy: 'Selin Arslan',
    folderId: 'campaigns',
    folderName: 'Kampanyalar',
    favorite: false,
    trashed: false,
    duration: '00:48',
    description: 'Türkçe seslendirme — lansman spotu.',
    tags: ['ses', 'voiceover', 'tr'],
    usages: [],
    history: [hist('h1', 'Yüklendi', 'Selin Arslan', '30 Tem 2026, 10:15')],
  },
  {
    id: 'a11',
    name: 'floorplan-a1.svg',
    kind: 'template',
    ext: 'SVG',
    sizeLabel: '220 KB',
    sizeBytes: 220_000,
    dateLabel: '1h önce',
    addedAt: '28 Temmuz 2026, 12:00',
    addedBy: 'Can Yıldız',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: false,
    trashed: false,
    description: 'A1 tipi kat planı şablonu.',
    tags: ['kat planı', 'şablon', 'svg'],
    usages: [USAGE_BRB, USAGE_WB],
    history: [hist('h1', 'Yüklendi', 'Can Yıldız', '28 Tem 2026, 12:00')],
  },
  {
    id: 'a12',
    name: 'sales-brief.docx',
    kind: 'document',
    ext: 'DOCX',
    sizeLabel: '840 KB',
    sizeBytes: 840_000,
    dateLabel: '1h önce',
    addedAt: '28 Temmuz 2026, 09:40',
    addedBy: 'Mehmet Kaya',
    folderId: 'documents',
    folderName: 'Belgeler',
    favorite: false,
    trashed: false,
    description: 'Satış brief dokümanı.',
    tags: ['brief', 'satış', 'docx'],
    usages: [],
    history: [hist('h1', 'Yüklendi', 'Mehmet Kaya', '28 Tem 2026, 09:40')],
  },
  {
    id: 'a13',
    name: 'amenity-gym.jpg',
    kind: 'image',
    ext: 'JPG',
    sizeLabel: '2.9 MB',
    sizeBytes: 2_900_000,
    dateLabel: '1h önce',
    addedAt: '27 Temmuz 2026, 15:10',
    addedBy: 'Ayşe Demir',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: false,
    trashed: false,
    thumbUrl: THUMBS[6],
    resolution: '3600×2400',
    description: 'Spor salonu renderı.',
    tags: ['gym', 'amenity'],
    usages: [USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Ayşe Demir', '27 Tem 2026, 15:10')],
  },
  {
    id: 'a14',
    name: 'reels-cut-02.mp4',
    kind: 'video',
    ext: 'MP4',
    sizeLabel: '34.5 MB',
    sizeBytes: 34_500_000,
    dateLabel: '1h önce',
    addedAt: '27 Temmuz 2026, 18:45',
    addedBy: 'Can Yıldız',
    folderId: 'social',
    folderName: 'Sosyal Medya',
    favorite: true,
    trashed: false,
    thumbUrl: THUMBS[7],
    duration: '00:22',
    resolution: '1080×1920',
    description: 'Reels kısa kesim — lifestyle.',
    tags: ['reels', 'sosyal', 'video'],
    usages: [USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Can Yıldız', '27 Tem 2026, 18:45')],
  },
  {
    id: 'a15',
    name: 'old-hero-backup.jpg',
    kind: 'image',
    ext: 'JPG',
    sizeLabel: '1.2 MB',
    sizeBytes: 1_200_000,
    dateLabel: '2h önce',
    addedAt: '21 Temmuz 2026, 08:00',
    addedBy: 'Ayşe Demir',
    folderId: 'temple',
    folderName: 'THE TEMPLE Residences',
    favorite: false,
    trashed: true,
    thumbUrl: THUMBS[0],
    resolution: '1920×1080',
    description: 'Eski hero yedeği — çöp kutusunda.',
    tags: ['yedek', 'eski'],
    usages: [],
    history: [
      hist('h1', 'Yüklendi', 'Ayşe Demir', '10 Tem 2026, 08:00'),
      hist('h2', 'Çöp kutusuna taşındı', 'Ayşe Demir', '21 Tem 2026, 08:00'),
    ],
  },
  {
    id: 'a16',
    name: 'ambient-loop.wav',
    kind: 'audio',
    ext: 'WAV',
    sizeLabel: '18.0 MB',
    sizeBytes: 18_000_000,
    dateLabel: '2h önce',
    addedAt: '20 Temmuz 2026, 11:30',
    addedBy: 'Selin Arslan',
    folderId: 'campaigns',
    folderName: 'Kampanyalar',
    favorite: false,
    trashed: false,
    duration: '02:10',
    description: 'Ambient müzik loop.',
    tags: ['müzik', 'ambient'],
    usages: [],
    history: [hist('h1', 'Yüklendi', 'Selin Arslan', '20 Tem 2026, 11:30')],
  },
  {
    id: 'a17',
    name: 'terrace-night.png',
    kind: 'image',
    ext: 'PNG',
    sizeLabel: '7.3 MB',
    sizeBytes: 7_300_000,
    dateLabel: '3h önce',
    addedAt: '18 Temmuz 2026, 21:00',
    addedBy: 'Ayşe Demir',
    folderId: 'renders',
    folderName: '3B Renderlar',
    favorite: false,
    trashed: false,
    thumbUrl: THUMBS[2],
    resolution: '4096×2304',
    description: 'Teras gece görünümü.',
    tags: ['teras', 'gece', 'render'],
    usages: [USAGE_BRB],
    history: [hist('h1', 'Yüklendi', 'Ayşe Demir', '18 Tem 2026, 21:00')],
  },
  {
    id: 'a18',
    name: 'launch-story-tpl.png',
    kind: 'template',
    ext: 'PNG',
    sizeLabel: '980 KB',
    sizeBytes: 980_000,
    dateLabel: '3h önce',
    addedAt: '17 Temmuz 2026, 13:15',
    addedBy: 'Can Yıldız',
    folderId: 'social',
    folderName: 'Sosyal Medya',
    favorite: true,
    trashed: false,
    thumbUrl: THUMBS[4],
    resolution: '1080×1920',
    description: 'Lansman story şablonu.',
    tags: ['şablon', 'story', 'sosyal'],
    usages: [USAGE_SMB],
    history: [hist('h1', 'Yüklendi', 'Can Yıldız', '17 Tem 2026, 13:15')],
  },
];

export const TOTAL_ASSET_COUNT = 1248;

export function kindMatchesSidebar(kind: AssetKind, sidebar: SidebarTypeId): boolean {
  if (sidebar === 'all' || sidebar === 'favorites' || sidebar === 'trash') return true;
  if (sidebar === 'images') return kind === 'image';
  if (sidebar === 'videos') return kind === 'video';
  if (sidebar === 'documents') return kind === 'document';
  if (sidebar === 'audio') return kind === 'audio';
  if (sidebar === 'templates') return kind === 'template';
  if (sidebar === 'brand') return kind === 'brand';
  return true;
}

export function kindMatchesTab(kind: AssetKind, tab: CenterTabId): boolean {
  if (tab === 'all') return true;
  if (tab === 'images') return kind === 'image';
  if (tab === 'videos') return kind === 'video';
  if (tab === 'documents') return kind === 'document';
  if (tab === 'audio') return kind === 'audio';
  if (tab === 'other') return kind === 'template' || kind === 'brand' || kind === 'other';
  return true;
}

export function filterAssets(
  assets: MediaAsset[],
  opts: {
    sidebar: SidebarTypeId;
    tab: CenterTabId;
    folderId: string | null;
    query: string;
  },
): MediaAsset[] {
  const q = opts.query.trim().toLowerCase();
  return assets.filter((a) => {
    if (opts.sidebar === 'trash') {
      if (!a.trashed) return false;
    } else if (a.trashed) {
      return false;
    }
    if (opts.sidebar === 'favorites' && !a.favorite) return false;
    if (!kindMatchesSidebar(a.kind, opts.sidebar)) return false;
    if (!kindMatchesTab(a.kind, opts.tab)) return false;
    if (opts.folderId && a.folderId !== opts.folderId) return false;
    if (q) {
      const hay = `${a.name} ${a.description} ${a.tags.join(' ')} ${a.ext}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

export function sortAssets(assets: MediaAsset[], sort: SortKey): MediaAsset[] {
  const next = [...assets];
  next.sort((a, b) => {
    if (sort === 'nameAsc') return a.name.localeCompare(b.name);
    if (sort === 'sizeDesc') return b.sizeBytes - a.sizeBytes;
    if (sort === 'oldest') return a.addedAt.localeCompare(b.addedAt);
    return b.addedAt.localeCompare(a.addedAt);
  });
  return next;
}

export function docIcon(ext: FileExt): IhIconName {
  if (ext === 'PDF' || ext === 'DOCX' || ext === 'PPTX') return 'documents';
  if (ext === 'MP3' || ext === 'WAV') return 'activity';
  if (ext === 'SVG') return 'sparkles';
  return 'inventory';
}
