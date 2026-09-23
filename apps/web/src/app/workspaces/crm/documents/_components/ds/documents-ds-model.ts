import type { IhIconName } from '@/components/icons/ih-icons';

export type DocFileType =
  | 'pdf'
  | 'docx'
  | 'xlsx'
  | 'pptx'
  | 'dwg'
  | 'jpg'
  | 'png'
  | 'zip'
  | 'video'
  | 'cad'
  | 'other';

export type DocFolderKey =
  | 'contracts'
  | 'finance'
  | 'marketing'
  | 'legal'
  | 'construction'
  | 'general';

export type DocCategoryTab =
  | 'all'
  | 'recent'
  | 'favorites'
  | 'shared'
  | 'lead'
  | 'investor'
  | 'projects'
  | 'companies'
  | 'contracts'
  | 'finance'
  | 'marketing'
  | 'legal'
  | 'construction'
  | 'architecture'
  | 'permits'
  | 'technical'
  | 'presentations';

export type DocPreviewKind =
  | 'photo'
  | 'pdf'
  | 'docx'
  | 'xlsx'
  | 'pptx'
  | 'blueprint'
  | 'permit'
  | 'video'
  | 'zip'
  | 'icon';

export type DocShortcutKey =
  | 'recentUploads'
  | 'frequent'
  | 'mine'
  | 'shared'
  | 'trash';

export type DocEntityKind = 'lead' | 'investor' | 'project' | 'company' | 'opportunity';

export type DocViewMode = 'card' | 'list';

export type DocSortKey = 'newest' | 'oldest' | 'name_asc' | 'name_desc' | 'size' | 'type';

export type DocPreviewTab = 'preview' | 'details' | 'history' | 'shares';

export type DocActivityKind =
  | 'uploaded'
  | 'viewed'
  | 'downloaded'
  | 'shared'
  | 'versionUpdated'
  | 'commentAdded';

export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';

export type DocRelatedRecord = {
  kind: DocEntityKind;
  id: string;
  name: string;
  href: string;
};

export type DocShare = {
  id: string;
  name: string;
  email: string;
  access: 'view' | 'edit' | 'comment';
  sharedAt: string;
};

export type DocActivity = {
  id: string;
  kind: DocActivityKind;
  actor: string;
  label: string;
  timeLabel: string;
};

export type DocRecord = {
  id: string;
  name: string;
  fileType: DocFileType;
  folder: DocFolderKey;
  sizeLabel: string;
  sizeBytes: number;
  version: string;
  owner: string;
  createdBy: string;
  uploadedAt: string;
  updatedAt: string;
  language: string;
  isFavorite: boolean;
  isShared: boolean;
  isMine: boolean;
  isFrequent: boolean;
  isTrashed: boolean;
  isRecent: boolean;
  hasThumbnail: boolean;
  thumbnailUrl: string | null;
  previewKind: DocPreviewKind;
  tags: string[];
  related: DocRelatedRecord[];
  shares: DocShare[];
  activities: DocActivity[];
  previewHint: string;
  source: 'documents' | 'files';
};

export type DocFilters = {
  search: string;
  fileType: DocFileType | '';
  entity: DocEntityKind | '';
  tag: string;
  owner: string;
  dateFrom: string;
  dateTo: string;
  tab: DocCategoryTab;
  shortcut: DocShortcutKey | '';
  folder: DocFolderKey | '';
  entityNav: DocEntityKind | '';
  view: DocViewMode;
  sort: DocSortKey;
};

export const EMPTY_DOC_FILTERS: DocFilters = {
  search: '',
  fileType: '',
  entity: '',
  tag: '',
  owner: '',
  dateFrom: '',
  dateTo: '',
  tab: 'all',
  shortcut: '',
  folder: '',
  entityNav: '',
  view: 'card',
  sort: 'newest',
};

export const DOC_CATEGORY_TABS: DocCategoryTab[] = [
  'all',
  'recent',
  'favorites',
  'shared',
  'lead',
  'investor',
  'projects',
  'companies',
  'contracts',
  'finance',
  'marketing',
  'legal',
  'construction',
  'architecture',
  'permits',
  'technical',
  'presentations',
];

/** Stable Unsplash previews for photo / marketing fixtures (no npm deps). */
export const DOC_THUMB = {
  exterior:
    'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=720&h=480&q=80',
  lobby:
    'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=720&h=480&q=80',
  interior:
    'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=720&h=480&q=80',
  construction:
    'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=720&h=480&q=80',
  site:
    'https://images.unsplash.com/photo-1487958449943-2429e8be8625?auto=format&fit=crop&w=720&h=480&q=80',
  brochure:
    'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=720&h=480&q=80',
  drone:
    'https://images.unsplash.com/photo-1448630360428-65456885c650?auto=format&fit=crop&w=720&h=480&q=80',
} as const;

export const DOC_SHORTCUTS: DocShortcutKey[] = [
  'recentUploads',
  'frequent',
  'mine',
  'shared',
  'trash',
];

export const DOC_FOLDERS: DocFolderKey[] = [
  'contracts',
  'finance',
  'marketing',
  'legal',
  'construction',
  'general',
];

export const DOC_ENTITY_KINDS: DocEntityKind[] = [
  'lead',
  'investor',
  'project',
  'company',
];

export const DOC_FILE_TYPES: DocFileType[] = [
  'pdf',
  'docx',
  'xlsx',
  'pptx',
  'dwg',
  'jpg',
  'png',
  'zip',
  'video',
  'cad',
  'other',
];

export const DOC_SORT_KEYS: DocSortKey[] = [
  'newest',
  'oldest',
  'name_asc',
  'name_desc',
  'size',
  'type',
];

export const FILE_TYPE_ICON: Record<DocFileType, IhIconName> = {
  pdf: 'documents',
  docx: 'documents',
  xlsx: 'barChart',
  pptx: 'documents',
  dwg: 'projects',
  jpg: 'sparkles',
  png: 'sparkles',
  zip: 'inbox',
  video: 'activity',
  cad: 'projects',
  other: 'documents',
};

export const FOLDER_TONE: Record<DocFolderKey, StatusTone> = {
  contracts: 'info',
  finance: 'success',
  marketing: 'warning',
  legal: 'danger',
  construction: 'default',
  general: 'default',
};

export const ENTITY_HREF: Record<DocEntityKind, (id: string) => string> = {
  lead: (id) => `/workspaces/crm/leads/${id}`,
  investor: (id) => `/workspaces/crm/investors/${id}`,
  project: (id) => `/dashboard/projects/${id}`,
  company: (id) => `/workspaces/crm/companies/${id}`,
  opportunity: (id) => `/workspaces/crm/pipeline?id=${id}`,
};

export const STORAGE_USED_GB = 32.4;
export const STORAGE_TOTAL_GB = 100;

function parseDateLabel(label: string): number {
  const [d, m, y] = label.split('.').map(Number);
  if (!d || !m || !y) return 0;
  return Date.UTC(y, m - 1, d);
}

function act(
  id: string,
  kind: DocActivityKind,
  actor: string,
  label: string,
  timeLabel: string,
): DocActivity {
  return { id, kind, actor, label, timeLabel };
}

function share(
  id: string,
  name: string,
  email: string,
  access: DocShare['access'],
  sharedAt: string,
): DocShare {
  return { id, name, email, access, sharedAt };
}

function related(
  kind: DocEntityKind,
  id: string,
  name: string,
): DocRelatedRecord {
  return { kind, id, name, href: ENTITY_HREF[kind](id) };
}

/** Unified CRM Belgeler fixture — Investhome-style assets with realistic previews. */
export function makeDocumentsDsFixture(): DocRecord[] {
  return [
    {
      id: 'doc-temple-plan',
      name: 'The_Temple_Floor_Plan.pdf',
      fileType: 'pdf',
      folder: 'construction',
      sizeLabel: '4.8 MB',
      sizeBytes: 4_800_000,
      version: 'v3.2',
      owner: 'Ayşe Demir',
      createdBy: 'Can Özkan',
      uploadedAt: '24.07.2026',
      updatedAt: '27.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: true,
      isMine: true,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'blueprint',
      tags: ['Proje', 'Plan', 'Mimari', 'Önemli'],
      related: [
        related('project', 'temple', 'The Temple'),
        related('lead', 'zeynep-kaya', 'Zeynep Kaya'),
      ],
      shares: [
        share('s1', 'Zeynep Kaya', 'zeynep@example.com', 'view', '26.07.2026'),
        share('s2', 'Nova Capital', 'ops@novacapital.com', 'comment', '25.07.2026'),
        share('s3', 'Ahmet Yılmaz', 'ahmet@investhome.demo', 'edit', '24.07.2026'),
      ],
      activities: [
        act('a1', 'versionUpdated', 'Can Özkan', 'Sürüm v3.2 yüklendi', '1s önce'),
        act('a2', 'viewed', 'Zeynep Kaya', 'Belge görüntülendi', '3s önce'),
        act('a3', 'shared', 'Ayşe Demir', 'Nova Capital ile paylaşıldı', 'Dün'),
        act('a4', 'uploaded', 'Can Özkan', 'İlk sürüm yüklendi', '24.07.2026'),
      ],
      previewHint: 'Mimari kat planı — PDF önizleme',
      source: 'documents',
    },
    {
      id: 'doc-temple-exterior',
      name: 'The_Temple_Exterior_02.jpg',
      fileType: 'jpg',
      folder: 'marketing',
      sizeLabel: '5.2 MB',
      sizeBytes: 5_200_000,
      version: 'v1.1',
      owner: 'Ahmet Yılmaz',
      createdBy: 'Pazarlama',
      uploadedAt: '26.07.2026',
      updatedAt: '26.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: true,
      isMine: true,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.exterior,
      previewKind: 'photo',
      tags: ['Görsel', 'Pazarlama', 'Dış Cephe'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [share('s1', 'Broker Pack', 'brokers@investhome.demo', 'view', '26.07.2026')],
      activities: [
        act('a1', 'viewed', 'Ayşe Demir', 'Görüntülendi', '2s önce'),
        act('a2', 'uploaded', 'Pazarlama', 'Yüklendi', '26.07.2026'),
      ],
      previewHint: 'The Temple dış cephe görseli',
      source: 'files',
    },
    {
      id: 'doc-temple-lobby',
      name: 'The_Temple_Lobby_01.jpg',
      fileType: 'jpg',
      folder: 'marketing',
      sizeLabel: '4.1 MB',
      sizeBytes: 4_100_000,
      version: 'v1.0',
      owner: 'Ahmet Yılmaz',
      createdBy: 'Pazarlama',
      uploadedAt: '25.07.2026',
      updatedAt: '25.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.lobby,
      previewKind: 'photo',
      tags: ['Görsel', 'Pazarlama', 'Lobi'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [],
      activities: [act('a1', 'uploaded', 'Pazarlama', 'Yüklendi', '25.07.2026')],
      previewHint: 'The Temple lobi görseli',
      source: 'files',
    },
    {
      id: 'doc-sales-contract',
      name: 'Contract_Package_Satis.pdf',
      fileType: 'pdf',
      folder: 'contracts',
      sizeLabel: '2.4 MB',
      sizeBytes: 2_400_000,
      version: 'v2.1',
      owner: 'Ayşe Demir',
      createdBy: 'Mehmet Kaya',
      uploadedAt: '22.07.2026',
      updatedAt: '24.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: true,
      isMine: true,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'pdf',
      tags: ['Sözleşme', 'Satış', 'İmza'],
      related: [
        related('lead', 'ahmet-yilmaz', 'Ahmet Yılmaz'),
        related('project', 'marina', 'Marina Heights'),
        related('opportunity', 'opp-marina', 'Marina Unit A-12'),
      ],
      shares: [
        share('s1', 'Ahmet Yılmaz', 'ahmet@example.com', 'view', '23.07.2026'),
        share('s2', 'Hukuk', 'legal@investhome.demo', 'edit', '22.07.2026'),
      ],
      activities: [
        act('a1', 'shared', 'Ayşe Demir', 'Müşteri ile paylaşıldı', '2s önce'),
        act('a2', 'downloaded', 'Ahmet Yılmaz', 'İndirildi', 'Dün'),
        act('a3', 'uploaded', 'Mehmet Kaya', 'Yüklendi', '22.07.2026'),
      ],
      previewHint: 'Satış sözleşme paketi — PDF',
      source: 'files',
    },
    {
      id: 'doc-payment-plan',
      name: 'Payment_Schedule_Odeme.xlsx',
      fileType: 'xlsx',
      folder: 'finance',
      sizeLabel: '856 KB',
      sizeBytes: 856_000,
      version: 'v3.0',
      owner: 'Can Özkan',
      createdBy: 'Elif Yıldız',
      uploadedAt: '21.07.2026',
      updatedAt: '22.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: true,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'xlsx',
      tags: ['Finans', 'Ödeme'],
      related: [related('project', 'marina', 'Marina Heights')],
      shares: [share('s1', 'Finans', 'finance@investhome.demo', 'edit', '21.07.2026')],
      activities: [
        act('a1', 'versionUpdated', 'Elif Yıldız', 'v3.0 güncellendi', 'Dün'),
        act('a2', 'uploaded', 'Elif Yıldız', 'Yüklendi', '21.07.2026'),
      ],
      previewHint: 'Ödeme planı tablosu',
      source: 'files',
    },
    {
      id: 'doc-investor-deck',
      name: 'The_Temple_Investor_Presentation.pptx',
      fileType: 'pptx',
      folder: 'marketing',
      sizeLabel: '18.2 MB',
      sizeBytes: 18_200_000,
      version: 'v1.4',
      owner: 'Zeynep Arslan',
      createdBy: 'Zeynep Arslan',
      uploadedAt: '20.07.2026',
      updatedAt: '21.07.2026',
      language: 'EN',
      isFavorite: true,
      isShared: true,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'pptx',
      tags: ['Pazarlama', 'Yatırımcı', 'Sunum'],
      related: [
        related('investor', 'nova', 'Nova Capital'),
        related('company', 'nova-co', 'Nova Capital Ltd'),
        related('project', 'temple', 'The Temple'),
      ],
      shares: [
        share('s1', 'Nova Capital', 'ops@novacapital.com', 'view', '20.07.2026'),
        share('s2', 'Horizon', 'ir@horizon.com', 'view', '20.07.2026'),
      ],
      activities: [
        act('a1', 'viewed', 'Nova Capital', 'Görüntülendi', '5s önce'),
        act('a2', 'uploaded', 'Zeynep Arslan', 'Yüklendi', '20.07.2026'),
      ],
      previewHint: 'Yatırımcı sunumu — PPTX',
      source: 'files',
    },
    {
      id: 'doc-building-permit',
      name: 'Building_Permit_Ruhsat.pdf',
      fileType: 'pdf',
      folder: 'legal',
      sizeLabel: '3.2 MB',
      sizeBytes: 3_200_000,
      version: 'v1.0',
      owner: 'Elif Yıldız',
      createdBy: 'Hukuk Ekibi',
      uploadedAt: '18.07.2026',
      updatedAt: '18.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'permit',
      tags: ['Hukuk', 'Ruhsat', 'İzin'],
      related: [related('project', 'ocean', 'Ocean View')],
      shares: [],
      activities: [act('a1', 'uploaded', 'Hukuk Ekibi', 'Yüklendi', '18.07.2026')],
      previewHint: 'Yapı ruhsatı belgesi',
      source: 'documents',
    },
    {
      id: 'doc-unit-photo',
      name: 'The_Temple_Interior_Unit_A12.jpg',
      fileType: 'jpg',
      folder: 'marketing',
      sizeLabel: '2.8 MB',
      sizeBytes: 2_800_000,
      version: 'v1.0',
      owner: 'Ahmet Yılmaz',
      createdBy: 'Ahmet Yılmaz',
      uploadedAt: '16.07.2026',
      updatedAt: '16.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.interior,
      previewKind: 'photo',
      tags: ['Görsel', 'Pazarlama', 'İç Mekân'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [],
      activities: [
        act('a1', 'viewed', 'Ayşe Demir', 'Görüntülendi', 'Dün'),
        act('a2', 'uploaded', 'Ahmet Yılmaz', 'Yüklendi', '16.07.2026'),
      ],
      previewHint: 'Birim iç mekân fotoğrafı',
      source: 'files',
    },
    {
      id: 'doc-nda-pack',
      name: 'NDA_Agreement_Horizon.pdf',
      fileType: 'pdf',
      folder: 'legal',
      sizeLabel: '1.4 MB',
      sizeBytes: 1_400_000,
      version: 'v2.0',
      owner: 'Ayşe Demir',
      createdBy: 'Hukuk Ekibi',
      uploadedAt: '12.07.2026',
      updatedAt: '14.07.2026',
      language: 'EN',
      isFavorite: false,
      isShared: true,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'docx',
      tags: ['Hukuk', 'NDA'],
      related: [related('investor', 'horizon', 'Horizon Partners')],
      shares: [share('s1', 'Horizon Partners', 'legal@horizon.com', 'view', '13.07.2026')],
      activities: [
        act('a1', 'shared', 'Ayşe Demir', 'Paylaşıldı', '13.07.2026'),
        act('a2', 'uploaded', 'Hukuk Ekibi', 'Yüklendi', '12.07.2026'),
      ],
      previewHint: 'NDA gizlilik sözleşmesi',
      source: 'files',
    },
    {
      id: 'doc-site-plan',
      name: 'The_Temple_Site_Plan.png',
      fileType: 'png',
      folder: 'construction',
      sizeLabel: '6.1 MB',
      sizeBytes: 6_100_000,
      version: 'v1.2',
      owner: 'Can Özkan',
      createdBy: 'Mimari Ofis',
      uploadedAt: '10.07.2026',
      updatedAt: '11.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.site,
      previewKind: 'photo',
      tags: ['İnşaat', 'Plan', 'Mimari', 'Vaziyet'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [],
      activities: [act('a1', 'uploaded', 'Mimari Ofis', 'Yüklendi', '10.07.2026')],
      previewHint: 'Vaziyet planı görseli',
      source: 'files',
    },
    {
      id: 'doc-reservation',
      name: 'Rezervasyon_Formu.docx',
      fileType: 'docx',
      folder: 'contracts',
      sizeLabel: '420 KB',
      sizeBytes: 420_000,
      version: 'v1.2',
      owner: 'Zeynep Arslan',
      createdBy: 'Zeynep Arslan',
      uploadedAt: '09.07.2026',
      updatedAt: '09.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'docx',
      tags: ['Sözleşme', 'Rezervasyon'],
      related: [
        related('lead', 'layla', 'Layla Mansour'),
        related('project', 'sunset', 'Sunset Blvd'),
      ],
      shares: [],
      activities: [act('a1', 'uploaded', 'Zeynep Arslan', 'Yüklendi', '09.07.2026')],
      previewHint: 'Rezervasyon formu',
      source: 'documents',
    },
    {
      id: 'doc-construction-progress',
      name: 'Construction_Progress_Report.pdf',
      fileType: 'pdf',
      folder: 'construction',
      sizeLabel: '7.6 MB',
      sizeBytes: 7_600_000,
      version: 'v2.0',
      owner: 'Can Özkan',
      createdBy: 'Şantiye',
      uploadedAt: '08.07.2026',
      updatedAt: '27.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: true,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.construction,
      previewKind: 'photo',
      tags: ['İnşaat', 'Rapor', 'Teknik'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [share('s1', 'Proje Ofisi', 'projects@investhome.demo', 'view', '08.07.2026')],
      activities: [
        act('a1', 'versionUpdated', 'Şantiye', 'v2.0 yüklendi', '27.07.2026'),
        act('a2', 'uploaded', 'Şantiye', 'Yüklendi', '08.07.2026'),
      ],
      previewHint: 'İnşaat ilerleme raporu',
      source: 'documents',
    },
    {
      id: 'doc-financial-analysis',
      name: 'Budget_Spreadsheet_Butce.xlsx',
      fileType: 'xlsx',
      folder: 'finance',
      sizeLabel: '1.8 MB',
      sizeBytes: 1_800_000,
      version: 'v2.0',
      owner: 'Elif Yıldız',
      createdBy: 'Elif Yıldız',
      uploadedAt: '07.07.2026',
      updatedAt: '08.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: false,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'xlsx',
      tags: ['Finans', 'Bütçe', 'Analiz'],
      related: [
        related('project', 'garden', 'Garden Court'),
        related('company', 'atlas', 'Atlas Realty'),
      ],
      shares: [],
      activities: [
        act('a1', 'commentAdded', 'Can Özkan', 'Yorum eklendi', '08.07.2026'),
        act('a2', 'uploaded', 'Elif Yıldız', 'Yüklendi', '07.07.2026'),
      ],
      previewHint: 'Bütçe tablosu',
      source: 'documents',
    },
    {
      id: 'doc-power-of-attorney',
      name: 'Vekaletname.pdf',
      fileType: 'pdf',
      folder: 'legal',
      sizeLabel: '980 KB',
      sizeBytes: 980_000,
      version: 'v1.1',
      owner: 'Burak Şahin',
      createdBy: 'Hukuk Ekibi',
      uploadedAt: '06.07.2026',
      updatedAt: '06.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: true,
      isMine: false,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'pdf',
      tags: ['Hukuk', 'Vekalet'],
      related: [related('lead', 'burak', 'Burak Şahin')],
      shares: [share('s1', 'Noter', 'noter@example.com', 'view', '06.07.2026')],
      activities: [act('a1', 'uploaded', 'Hukuk Ekibi', 'Yüklendi', '06.07.2026')],
      previewHint: 'Vekaletname',
      source: 'documents',
    },
    {
      id: 'doc-cad-facade',
      name: 'Cephe_Detay_Blueprint.dwg',
      fileType: 'dwg',
      folder: 'construction',
      sizeLabel: '22.5 MB',
      sizeBytes: 22_500_000,
      version: 'v4.0',
      owner: 'Can Özkan',
      createdBy: 'Mimari Ofis',
      uploadedAt: '05.07.2026',
      updatedAt: '15.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'blueprint',
      tags: ['CAD', 'İnşaat', 'Mimari', 'Teknik'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [],
      activities: [
        act('a1', 'versionUpdated', 'Mimari Ofis', 'v4.0 yüklendi', '15.07.2026'),
        act('a2', 'uploaded', 'Mimari Ofis', 'Yüklendi', '05.07.2026'),
      ],
      previewHint: 'CAD cephe detay çizimi',
      source: 'files',
    },
    {
      id: 'doc-walkthrough',
      name: 'The_Temple_Drone_Walkthrough.mp4',
      fileType: 'video',
      folder: 'marketing',
      sizeLabel: '148 MB',
      sizeBytes: 148_000_000,
      version: 'v1.0',
      owner: 'Zeynep Arslan',
      createdBy: 'Pazarlama',
      uploadedAt: '03.07.2026',
      updatedAt: '03.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: true,
      isMine: false,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.drone,
      previewKind: 'video',
      tags: ['Video', 'Pazarlama', 'Drone'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [share('s1', 'Broker Pack', 'brokers@investhome.demo', 'view', '04.07.2026')],
      activities: [
        act('a1', 'downloaded', 'Atlas Realty', 'İndirildi', '05.07.2026'),
        act('a2', 'uploaded', 'Pazarlama', 'Yüklendi', '03.07.2026'),
      ],
      previewHint: 'Drone sanal tur videosu',
      source: 'files',
    },
    {
      id: 'doc-brochure',
      name: 'The_Temple_Marketing_Brochure.pdf',
      fileType: 'pdf',
      folder: 'marketing',
      sizeLabel: '8.4 MB',
      sizeBytes: 8_400_000,
      version: 'v2.3',
      owner: 'Zeynep Arslan',
      createdBy: 'Pazarlama',
      uploadedAt: '01.07.2026',
      updatedAt: '19.07.2026',
      language: 'EN',
      isFavorite: false,
      isShared: true,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: DOC_THUMB.brochure,
      previewKind: 'photo',
      tags: ['Pazarlama', 'Broşür', 'Sunum'],
      related: [
        related('project', 'temple', 'The Temple'),
        related('company', 'atlas', 'Atlas Realty'),
      ],
      shares: [
        share('s1', 'Atlas Realty', 'sales@atlas.com', 'view', '02.07.2026'),
        share('s2', 'Broker Pool', 'brokers@investhome.demo', 'view', '02.07.2026'),
      ],
      activities: [
        act('a1', 'versionUpdated', 'Pazarlama', 'v2.3 yüklendi', '19.07.2026'),
        act('a2', 'uploaded', 'Pazarlama', 'Yüklendi', '01.07.2026'),
      ],
      previewHint: 'Proje pazarlama broşürü',
      source: 'documents',
    },
    {
      id: 'doc-budget',
      name: 'Insaat_Butcesi_v5.xlsx',
      fileType: 'xlsx',
      folder: 'finance',
      sizeLabel: '2.1 MB',
      sizeBytes: 2_100_000,
      version: 'v5.1',
      owner: 'Elif Yıldız',
      createdBy: 'Finans',
      uploadedAt: '28.06.2026',
      updatedAt: '20.07.2026',
      language: 'TR',
      isFavorite: true,
      isShared: false,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'xlsx',
      tags: ['Finans', 'Bütçe', 'İnşaat'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [],
      activities: [
        act('a1', 'versionUpdated', 'Finans', 'v5.1 yüklendi', '20.07.2026'),
        act('a2', 'uploaded', 'Finans', 'Yüklendi', '28.06.2026'),
      ],
      previewHint: 'İnşaat bütçe tablosu',
      source: 'documents',
    },
    {
      id: 'doc-trashed-draft',
      name: 'Taslak_Sozlesme_eski.docx',
      fileType: 'docx',
      folder: 'contracts',
      sizeLabel: '310 KB',
      sizeBytes: 310_000,
      version: 'v0.9',
      owner: 'Ayşe Demir',
      createdBy: 'Ayşe Demir',
      uploadedAt: '15.06.2026',
      updatedAt: '15.06.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: true,
      isRecent: false,
      hasThumbnail: false,
      thumbnailUrl: null,
      previewKind: 'icon',
      tags: ['Taslak'],
      related: [],
      shares: [],
      activities: [act('a1', 'uploaded', 'Ayşe Demir', 'Çöp kutusuna taşındı', '15.06.2026')],
      previewHint: 'Silinmiş taslak',
      source: 'documents',
    },
    {
      id: 'doc-cad-model',
      name: '3D_BIM_Model_Technical.ifc',
      fileType: 'cad',
      folder: 'construction',
      sizeLabel: '64 MB',
      sizeBytes: 64_000_000,
      version: 'v2.0',
      owner: 'Can Özkan',
      createdBy: 'BIM Ekibi',
      uploadedAt: '25.06.2026',
      updatedAt: '12.07.2026',
      language: 'EN',
      isFavorite: false,
      isShared: false,
      isMine: false,
      isFrequent: false,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'blueprint',
      tags: ['CAD', 'BIM', 'Teknik'],
      related: [related('project', 'skyline', 'Skyline Lofts')],
      shares: [],
      activities: [act('a1', 'uploaded', 'BIM Ekibi', 'Yüklendi', '25.06.2026')],
      previewHint: 'BIM teknik model önizlemesi',
      source: 'files',
    },
    {
      id: 'doc-company-profile',
      name: 'Sirket_Profili_Atlas.docx',
      fileType: 'docx',
      folder: 'general',
      sizeLabel: '1.4 MB',
      sizeBytes: 1_400_000,
      version: 'v1.0',
      owner: 'Mehmet Kaya',
      createdBy: 'Mehmet Kaya',
      uploadedAt: '19.07.2026',
      updatedAt: '19.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: true,
      isFrequent: false,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'docx',
      tags: ['Şirket'],
      related: [related('company', 'atlas', 'Atlas Realty')],
      shares: [],
      activities: [act('a1', 'uploaded', 'Mehmet Kaya', 'Yüklendi', '19.07.2026')],
      previewHint: 'Şirket profili',
      source: 'documents',
    },
    {
      id: 'doc-investor-kyc',
      name: 'KYC_Package_Nova.pdf',
      fileType: 'pdf',
      folder: 'legal',
      sizeLabel: '5.6 MB',
      sizeBytes: 5_600_000,
      version: 'v1.3',
      owner: 'Ayşe Demir',
      createdBy: 'Uyumluluk',
      uploadedAt: '17.07.2026',
      updatedAt: '25.07.2026',
      language: 'EN',
      isFavorite: true,
      isShared: true,
      isMine: true,
      isFrequent: true,
      isTrashed: false,
      isRecent: true,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'pdf',
      tags: ['KYC', 'Yatırımcı', 'Hukuk'],
      related: [
        related('investor', 'nova', 'Nova Capital'),
        related('lead', 'elena', 'Elena Petrova'),
      ],
      shares: [
        share('s1', 'Uyumluluk', 'compliance@investhome.demo', 'edit', '17.07.2026'),
        share('s2', 'Nova Capital', 'kyc@novacapital.com', 'view', '18.07.2026'),
      ],
      activities: [
        act('a1', 'versionUpdated', 'Uyumluluk', 'v1.3 yüklendi', '25.07.2026'),
        act('a2', 'shared', 'Ayşe Demir', 'Paylaşıldı', '18.07.2026'),
        act('a3', 'uploaded', 'Uyumluluk', 'Yüklendi', '17.07.2026'),
      ],
      previewHint: 'KYC uyumluluk paketi',
      source: 'documents',
    },
    {
      id: 'doc-tech-spec',
      name: 'Technical_Specs_Mekanik.pdf',
      fileType: 'pdf',
      folder: 'construction',
      sizeLabel: '3.9 MB',
      sizeBytes: 3_900_000,
      version: 'v1.5',
      owner: 'Can Özkan',
      createdBy: 'Teknik Ofis',
      uploadedAt: '04.07.2026',
      updatedAt: '14.07.2026',
      language: 'TR',
      isFavorite: false,
      isShared: false,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'pdf',
      tags: ['Teknik', 'Mekanik', 'İnşaat'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [],
      activities: [act('a1', 'uploaded', 'Teknik Ofis', 'Yüklendi', '04.07.2026')],
      previewHint: 'Mekanik teknik şartname',
      source: 'documents',
    },
    {
      id: 'doc-arch-elevations',
      name: 'Architectural_Elevations.pdf',
      fileType: 'pdf',
      folder: 'construction',
      sizeLabel: '9.2 MB',
      sizeBytes: 9_200_000,
      version: 'v2.1',
      owner: 'Can Özkan',
      createdBy: 'Mimari Ofis',
      uploadedAt: '02.07.2026',
      updatedAt: '16.07.2026',
      language: 'EN',
      isFavorite: true,
      isShared: true,
      isMine: false,
      isFrequent: true,
      isTrashed: false,
      isRecent: false,
      hasThumbnail: true,
      thumbnailUrl: null,
      previewKind: 'blueprint',
      tags: ['Mimari', 'Plan', 'Teknik'],
      related: [related('project', 'temple', 'The Temple')],
      shares: [share('s1', 'Mimari', 'arch@investhome.demo', 'edit', '02.07.2026')],
      activities: [
        act('a1', 'versionUpdated', 'Mimari Ofis', 'v2.1 yüklendi', '16.07.2026'),
        act('a2', 'uploaded', 'Mimari Ofis', 'Yüklendi', '02.07.2026'),
      ],
      previewHint: 'Mimari cephe görünüşleri',
      source: 'documents',
    },
  ];
}

export function matchesTab(doc: DocRecord, tab: DocCategoryTab): boolean {
  if (doc.isTrashed && tab !== 'all') return false;
  switch (tab) {
    case 'all':
      return !doc.isTrashed;
    case 'recent':
      return doc.isRecent && !doc.isTrashed;
    case 'favorites':
      return doc.isFavorite && !doc.isTrashed;
    case 'shared':
      return doc.isShared && !doc.isTrashed;
    case 'lead':
      return doc.related.some((r) => r.kind === 'lead') && !doc.isTrashed;
    case 'investor':
      return doc.related.some((r) => r.kind === 'investor') && !doc.isTrashed;
    case 'projects':
      return doc.related.some((r) => r.kind === 'project') && !doc.isTrashed;
    case 'companies':
      return doc.related.some((r) => r.kind === 'company') && !doc.isTrashed;
    case 'contracts':
      return doc.folder === 'contracts' && !doc.isTrashed;
    case 'finance':
      return doc.folder === 'finance' && !doc.isTrashed;
    case 'marketing':
      return doc.folder === 'marketing' && !doc.isTrashed;
    case 'legal':
      return doc.folder === 'legal' && !doc.isTrashed;
    case 'construction':
      return (
        (doc.folder === 'construction' || doc.tags.some((t) => /in[şs]aat|construction/i.test(t))) &&
        !doc.isTrashed
      );
    case 'architecture':
      return doc.tags.some((t) => /mimari|architecture|plan/i.test(t)) && !doc.isTrashed;
    case 'permits':
      return doc.tags.some((t) => /ruhsat|izin|permit|tapu/i.test(t)) && !doc.isTrashed;
    case 'technical':
      return (
        (doc.tags.some((t) => /teknik|cad|bim|technical/i.test(t)) ||
          doc.fileType === 'dwg' ||
          doc.fileType === 'cad') &&
        !doc.isTrashed
      );
    case 'presentations':
      return (
        (doc.fileType === 'pptx' || doc.tags.some((t) => /sunum|bro[şs]ür|presentation/i.test(t))) &&
        !doc.isTrashed
      );
    default:
      return !doc.isTrashed;
  }
}

export function matchesShortcut(doc: DocRecord, shortcut: DocShortcutKey): boolean {
  switch (shortcut) {
    case 'recentUploads':
      return doc.isRecent && !doc.isTrashed;
    case 'frequent':
      return doc.isFrequent && !doc.isTrashed;
    case 'mine':
      return doc.isMine && !doc.isTrashed;
    case 'shared':
      return doc.isShared && !doc.isTrashed;
    case 'trash':
      return doc.isTrashed;
    default:
      return true;
  }
}

export function countByTab(docs: DocRecord[], tab: DocCategoryTab): number {
  return docs.filter((d) => matchesTab(d, tab)).length;
}

export function countByShortcut(docs: DocRecord[], key: DocShortcutKey): number {
  return docs.filter((d) => matchesShortcut(d, key)).length;
}

export function countByFolder(docs: DocRecord[], folder: DocFolderKey): number {
  return docs.filter((d) => d.folder === folder && !d.isTrashed).length;
}

export function countByEntity(docs: DocRecord[], kind: DocEntityKind): number {
  return docs.filter((d) => !d.isTrashed && d.related.some((r) => r.kind === kind)).length;
}

export function uniqueOwners(docs: DocRecord[]): string[] {
  return [...new Set(docs.filter((d) => !d.isTrashed).map((d) => d.owner))].sort();
}

export function uniqueTags(docs: DocRecord[]): string[] {
  return [...new Set(docs.filter((d) => !d.isTrashed).flatMap((d) => d.tags))].sort();
}

export function filterDocuments(docs: DocRecord[], filters: DocFilters): DocRecord[] {
  let result = docs.slice();

  if (filters.shortcut) {
    result = result.filter((d) => matchesShortcut(d, filters.shortcut as DocShortcutKey));
  } else if (filters.folder) {
    result = result.filter((d) => d.folder === filters.folder && !d.isTrashed);
  } else if (filters.entityNav) {
    result = result.filter(
      (d) => !d.isTrashed && d.related.some((r) => r.kind === filters.entityNav),
    );
  } else {
    result = result.filter((d) => matchesTab(d, filters.tab));
  }

  const q = filters.search.trim().toLowerCase();
  if (q) {
    result = result.filter(
      (d) =>
        d.name.toLowerCase().includes(q) ||
        d.owner.toLowerCase().includes(q) ||
        d.tags.some((t) => t.toLowerCase().includes(q)) ||
        d.related.some((r) => r.name.toLowerCase().includes(q)),
    );
  }

  if (filters.fileType) {
    result = result.filter((d) => d.fileType === filters.fileType);
  }
  if (filters.entity) {
    result = result.filter((d) => d.related.some((r) => r.kind === filters.entity));
  }
  if (filters.tag) {
    result = result.filter((d) => d.tags.includes(filters.tag));
  }
  if (filters.owner) {
    result = result.filter((d) => d.owner === filters.owner);
  }
  if (filters.dateFrom) {
    const from = Date.parse(filters.dateFrom);
    if (!Number.isNaN(from)) {
      result = result.filter((d) => parseDateLabel(d.uploadedAt) >= from);
    }
  }
  if (filters.dateTo) {
    const to = Date.parse(filters.dateTo);
    if (!Number.isNaN(to)) {
      result = result.filter((d) => parseDateLabel(d.uploadedAt) <= to + 86_400_000);
    }
  }

  return sortDocuments(result, filters.sort);
}

export function sortDocuments(docs: DocRecord[], sort: DocSortKey): DocRecord[] {
  const sorted = docs.slice();
  sorted.sort((a, b) => {
    switch (sort) {
      case 'oldest':
        return parseDateLabel(a.uploadedAt) - parseDateLabel(b.uploadedAt);
      case 'name_asc':
        return a.name.localeCompare(b.name, 'tr');
      case 'name_desc':
        return b.name.localeCompare(a.name, 'tr');
      case 'size':
        return b.sizeBytes - a.sizeBytes;
      case 'type':
        return a.fileType.localeCompare(b.fileType);
      case 'newest':
      default:
        return parseDateLabel(b.uploadedAt) - parseDateLabel(a.uploadedAt);
    }
  });
  return sorted;
}

export function fileTypeLabel(type: DocFileType): string {
  return type.toUpperCase();
}
