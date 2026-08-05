import type { IhIconName } from '@/components/icons/ih-icons';

import {
  ADS_BUILDER_ROUTE,
  BLOG_BUILDER_ROUTE,
  BROCHURE_BUILDER_ROUTE,
  EMAIL_BUILDER_ROUTE,
  LANDING_PAGE_BUILDER_ROUTE,
  PRESENTATION_BUILDER_ROUTE,
  PROPOSAL_BUILDER_ROUTE,
  SOCIAL_MEDIA_BUILDER_ROUTE,
  VIDEO_BUILDER_ROUTE,
  WEBSITE_BUILDER_ROUTE,
} from '../_components/ds/creative-studio-ds-model';

export const TM_HOME = '/workspaces/creative-studio';
export const TEMPLATES_ROUTE = '/workspaces/creative-studio/templates';

export type TemplateType =
  | 'website'
  | 'landing'
  | 'blog'
  | 'email'
  | 'social'
  | 'presentation'
  | 'proposal'
  | 'brochure'
  | 'ad'
  | 'video'
  | 'brandKit';

export type TemplateSource =
  | 'ai'
  | 'company'
  | 'personal'
  | 'favorites'
  | 'recent'
  | 'trash';

export type TemplatePackId =
  | 'luxury'
  | 'construction'
  | 'investor'
  | 'hotel'
  | 'corporate';

export type HeaderTabId = 'investhomeAi' | 'designAssistant' | 'trends' | 'templatePack';

export type SortKey = 'popular' | 'newest' | 'nameAsc';

export type DeviceKind = 'desktop' | 'tablet' | 'mobile';

export type QuickActionId = 'info' | 'preview' | 'clone' | 'favorite' | 'open' | 'delete';

export type CardActionId = 'open' | 'duplicate' | 'favorite' | 'share' | 'delete';

export type AiSuggestionId =
  | 'luxuryWebsite'
  | 'investorEmail'
  | 'investmentPresentation'
  | 'instagramCarousel';

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

export type StudioTemplate = {
  id: string;
  name: string;
  type: TemplateType;
  categoryLabel: string;
  source: TemplateSource;
  packId?: TemplatePackId;
  favorite: boolean;
  trashed: boolean;
  recentlyUsed: boolean;
  popularScore: number;
  devices: DeviceKind[];
  tags: string[];
  description: string;
  features: string[];
  usageSteps: string[];
  thumbUrl: string;
  gallery: string[];
  builderHref: string;
  colorHint: string;
};

export const HEADER_TABS: HeaderTabId[] = [
  'investhomeAi',
  'designAssistant',
  'trends',
  'templatePack',
];

export const CATEGORY_COUNTS: { id: TemplateType | 'all'; icon: IhIconName; count: number }[] = [
  { id: 'all', icon: 'inventory', count: 256 },
  { id: 'website', icon: 'design', count: 45 },
  { id: 'landing', icon: 'target', count: 58 },
  { id: 'blog', icon: 'documents', count: 24 },
  { id: 'email', icon: 'inbox', count: 32 },
  { id: 'social', icon: 'activity', count: 28 },
  { id: 'presentation', icon: 'target', count: 18 },
  { id: 'proposal', icon: 'documents', count: 20 },
  { id: 'brochure', icon: 'documents', count: 15 },
  { id: 'ad', icon: 'trendingUp', count: 16 },
];

export const SOURCE_ITEMS: { id: TemplateSource; icon: IhIconName; badge?: 'new' }[] = [
  { id: 'ai', icon: 'sparkles', badge: 'new' },
  { id: 'company', icon: 'projects' },
  { id: 'personal', icon: 'user' },
  { id: 'favorites', icon: 'check' },
  { id: 'recent', icon: 'clock' },
  { id: 'trash', icon: 'alert' },
];

export const PACK_ITEMS: { id: TemplatePackId; icon: IhIconName; count: number }[] = [
  { id: 'luxury', icon: 'sparkles', count: 24 },
  { id: 'construction', icon: 'projects', count: 18 },
  { id: 'investor', icon: 'trendingUp', count: 22 },
  { id: 'hotel', icon: 'home', count: 14 },
  { id: 'corporate', icon: 'executive', count: 16 },
];

export const QUICK_ACTIONS: { id: QuickActionId; icon: IhIconName }[] = [
  { id: 'info', icon: 'alert' },
  { id: 'preview', icon: 'search' },
  { id: 'clone', icon: 'documents' },
  { id: 'favorite', icon: 'check' },
  { id: 'open', icon: 'arrowRight' },
  { id: 'delete', icon: 'activity' },
];

export const CARD_ACTIONS: { id: CardActionId; icon: IhIconName }[] = [
  { id: 'open', icon: 'arrowRight' },
  { id: 'duplicate', icon: 'documents' },
  { id: 'favorite', icon: 'check' },
  { id: 'share', icon: 'users' },
  { id: 'delete', icon: 'alert' },
];

export const AI_SUGGESTIONS: AiSuggestionId[] = [
  'luxuryWebsite',
  'investorEmail',
  'investmentPresentation',
  'instagramCarousel',
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

export const DEVICE_ICONS: Record<DeviceKind, IhIconName> = {
  desktop: 'executive',
  tablet: 'documents',
  mobile: 'activity',
};

const THUMBS = [
  'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1560518883-ce09059eeffa?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1613490493576-7fde63acd811?auto=format&fit=crop&w=800&h=600&q=80',
  'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=800&h=600&q=80',
];

function galleryFrom(idx: number): string[] {
  return [0, 1, 2, 3].map((offset) => THUMBS[(idx + offset) % THUMBS.length]!);
}

function builderFor(type: TemplateType): string {
  switch (type) {
    case 'website':
      return WEBSITE_BUILDER_ROUTE;
    case 'landing':
      return LANDING_PAGE_BUILDER_ROUTE;
    case 'blog':
      return BLOG_BUILDER_ROUTE;
    case 'email':
      return EMAIL_BUILDER_ROUTE;
    case 'social':
      return SOCIAL_MEDIA_BUILDER_ROUTE;
    case 'presentation':
      return PRESENTATION_BUILDER_ROUTE;
    case 'proposal':
      return PROPOSAL_BUILDER_ROUTE;
    case 'brochure':
      return BROCHURE_BUILDER_ROUTE;
    case 'ad':
      return ADS_BUILDER_ROUTE;
    case 'video':
      return VIDEO_BUILDER_ROUTE;
    case 'brandKit':
      return WEBSITE_BUILDER_ROUTE;
  }
}

export const DEMO_TEMPLATES: StudioTemplate[] = [
  {
    id: 'tpl-1',
    name: 'Modern Luxury Landing',
    type: 'landing',
    categoryLabel: 'Landing Page',
    source: 'company',
    packId: 'luxury',
    favorite: true,
    trashed: false,
    recentlyUsed: true,
    popularScore: 98,
    devices: ['desktop', 'tablet', 'mobile'],
    tags: ['Landing Page', 'Lüks', 'Gayrimenkul'],
    description:
      'Lüks konut projeleri için modern ve zarif bir landing page şablonu. Hero, özellikler, galeri ve iletişim bölümleri içerir.',
    features: ['Tam responsive', '8+ bölüm', 'SEO uyumlu', 'Hızlı yükleme'],
    usageSteps: [
      'Şablonu klonlayın veya düzenleyicide açın',
      'Proje bilgilerini ve görselleri güncelleyin',
      'Renk ve tipografiyi markanıza uyarlayın',
      'Önizleyip yayınlayın',
    ],
    thumbUrl: THUMBS[0]!,
    gallery: galleryFrom(0),
    builderHref: builderFor('landing'),
    colorHint: '#075b75',
  },
  {
    id: 'tpl-2',
    name: 'Investor Website Pro',
    type: 'website',
    categoryLabel: 'Website',
    source: 'company',
    packId: 'investor',
    favorite: false,
    trashed: false,
    recentlyUsed: true,
    popularScore: 92,
    devices: ['desktop', 'tablet', 'mobile'],
    tags: ['Website', 'Yatırımcı', 'Kurumsal'],
    description:
      'Çok sayfalı yatırımcı web sitesi. Proje listesi, ROI hesaplayıcı ve iletişim formları hazır.',
    features: ['Çok sayfa', 'ROI widget', 'Blog entegrasyonu'],
    usageSteps: [
      'Website Builder’da açın',
      'Sayfa yapısını özelleştirin',
      'Proje verilerini bağlayın',
    ],
    thumbUrl: THUMBS[1]!,
    gallery: galleryFrom(1),
    builderHref: builderFor('website'),
    colorHint: '#1e2b33',
  },
  {
    id: 'tpl-3',
    name: 'Market Update Blog',
    type: 'blog',
    categoryLabel: 'Blog',
    source: 'ai',
    favorite: false,
    trashed: false,
    recentlyUsed: false,
    popularScore: 84,
    devices: ['desktop', 'mobile'],
    tags: ['Blog', 'Piyasa', 'SEO'],
    description: 'Piyasa güncellemeleri ve yatırım rehberleri için SEO odaklı blog şablonu.',
    features: ['SEO meta', 'İçindekiler', 'İlgili yazılar'],
    usageSteps: ['Blog Studio’da açın', 'Konuyu yazın', 'Yayınlayın'],
    thumbUrl: THUMBS[2]!,
    gallery: galleryFrom(2),
    builderHref: builderFor('blog'),
    colorHint: '#58aebb',
  },
  {
    id: 'tpl-4',
    name: 'Launch Email Sequence',
    type: 'email',
    categoryLabel: 'Email',
    source: 'company',
    packId: 'corporate',
    favorite: true,
    trashed: false,
    recentlyUsed: false,
    popularScore: 88,
    devices: ['desktop', 'mobile'],
    tags: ['Email', 'Lansman', 'Kampanya'],
    description: 'Proje lansmanı için 3 parçalı e-posta serisi şablonu.',
    features: ['Duyarlı tablo', 'CTA blokları', 'A/B başlık'],
    usageSteps: ['Email Studio’da açın', 'Metinleri düzenleyin', 'Gönderim planlayın'],
    thumbUrl: THUMBS[3]!,
    gallery: galleryFrom(3),
    builderHref: builderFor('email'),
    colorHint: '#075b75',
  },
  {
    id: 'tpl-5',
    name: 'Instagram Story Luxury',
    type: 'social',
    categoryLabel: 'Social',
    source: 'ai',
    packId: 'luxury',
    favorite: false,
    trashed: false,
    recentlyUsed: true,
    popularScore: 95,
    devices: ['mobile'],
    tags: ['Social', 'Story', 'Lüks'],
    description: 'Lüks proje hikâyeleri için dikey sosyal medya şablonu.',
    features: ['9:16', 'Marka renkleri', 'Hızlı metin alanları'],
    usageSteps: ['Social Studio’da açın', 'Görselleri değiştirin', 'Dışa aktarın'],
    thumbUrl: THUMBS[4]!,
    gallery: galleryFrom(4),
    builderHref: builderFor('social'),
    colorHint: '#58aebb',
  },
  {
    id: 'tpl-6',
    name: 'Investor Pitch Deck',
    type: 'presentation',
    categoryLabel: 'Presentation',
    source: 'company',
    packId: 'investor',
    favorite: true,
    trashed: false,
    recentlyUsed: false,
    popularScore: 90,
    devices: ['desktop', 'tablet'],
    tags: ['Presentation', 'Pitch', 'Yatırımcı'],
    description: 'Yatırımcı sunumu için 12 slaytlık profesyonel deck şablonu.',
    features: ['12 slayt', 'Finans tabloları', 'Marka kit uyumu'],
    usageSteps: ['Presentation Builder’da açın', 'Verileri doldurun', 'Önizleyin'],
    thumbUrl: THUMBS[5]!,
    gallery: galleryFrom(5),
    builderHref: builderFor('presentation'),
    colorHint: '#075b75',
  },
  {
    id: 'tpl-7',
    name: 'Sales Proposal Soft',
    type: 'proposal',
    categoryLabel: 'Proposal',
    source: 'personal',
    packId: 'corporate',
    favorite: false,
    trashed: false,
    recentlyUsed: false,
    popularScore: 76,
    devices: ['desktop', 'tablet', 'mobile'],
    tags: ['Proposal', 'Satış', 'Teklif'],
    description: 'Müşteri teklifleri için sade ve güven veren proposal şablonu.',
    features: ['Fiyat tablosu', 'İmza alanı', 'PDF hazır'],
    usageSteps: ['Proposal Builder’da açın', 'Teklif kalemlerini girin', 'Paylaşın'],
    thumbUrl: THUMBS[6]!,
    gallery: galleryFrom(6),
    builderHref: builderFor('proposal'),
    colorHint: '#1e2b33',
  },
  {
    id: 'tpl-8',
    name: 'Project Brochure Tri-Fold',
    type: 'brochure',
    categoryLabel: 'Brochure',
    source: 'company',
    packId: 'construction',
    favorite: false,
    trashed: false,
    recentlyUsed: true,
    popularScore: 81,
    devices: ['desktop'],
    tags: ['Brochure', 'İnşaat', 'Print'],
    description: 'Üç katlı baskı broşürü — planlar, özellikler ve iletişim.',
    features: ['A4/A5', 'Print-ready', 'Kat çizgileri'],
    usageSteps: ['Brochure Studio’da açın', 'İçeriği güncelleyin', 'PDF dışa aktarın'],
    thumbUrl: THUMBS[7]!,
    gallery: galleryFrom(7),
    builderHref: builderFor('brochure'),
    colorHint: '#075b75',
  },
  {
    id: 'tpl-9',
    name: 'Meta Ad — Soft Launch',
    type: 'ad',
    categoryLabel: 'Ad',
    source: 'ai',
    packId: 'hotel',
    favorite: false,
    trashed: false,
    recentlyUsed: false,
    popularScore: 87,
    devices: ['mobile', 'desktop'],
    tags: ['Ad', 'Meta', 'Kampanya'],
    description: 'Soft launch kampanyaları için kare ve story reklam seti.',
    features: ['1:1 + 9:16', 'CTA varyasyonları', 'Marka güvenli'],
    usageSteps: ['Ads Builder’da açın', 'Varyasyon seçin', 'Dışa aktarın'],
    thumbUrl: THUMBS[0]!,
    gallery: galleryFrom(0),
    builderHref: builderFor('ad'),
    colorHint: '#58aebb',
  },
  {
    id: 'tpl-10',
    name: 'Residence Walkthrough',
    type: 'video',
    categoryLabel: 'Video',
    source: 'company',
    packId: 'luxury',
    favorite: true,
    trashed: false,
    recentlyUsed: false,
    popularScore: 79,
    devices: ['desktop', 'mobile'],
    tags: ['Video', 'Walkthrough', 'Lüks'],
    description: 'Rezidans tanıtım videosu için sahne ve metin şablonu.',
    features: ['Sahne timeline', 'Altyazı', 'Müzik yuvası'],
    usageSteps: ['Video Studio’da açın', 'Klipleri yerleştirin', 'Dışa aktarın'],
    thumbUrl: THUMBS[1]!,
    gallery: galleryFrom(1),
    builderHref: builderFor('video'),
    colorHint: '#075b75',
  },
  {
    id: 'tpl-11',
    name: 'My Draft Landing',
    type: 'landing',
    categoryLabel: 'Landing Page',
    source: 'personal',
    favorite: false,
    trashed: false,
    recentlyUsed: true,
    popularScore: 40,
    devices: ['desktop', 'mobile'],
    tags: ['Kişisel', 'Taslak'],
    description: 'Kişisel taslak landing — henüz yayınlanmadı.',
    features: ['Taslak', '2 bölüm'],
    usageSteps: ['Düzenleyicide açın', 'İçeriği tamamlayın'],
    thumbUrl: THUMBS[2]!,
    gallery: galleryFrom(2),
    builderHref: builderFor('landing'),
    colorHint: '#718087',
  },
  {
    id: 'tpl-12',
    name: 'Archived Ad Set',
    type: 'ad',
    categoryLabel: 'Ad',
    source: 'trash',
    favorite: false,
    trashed: true,
    recentlyUsed: false,
    popularScore: 10,
    devices: ['mobile'],
    tags: ['Arşiv'],
    description: 'Çöp kutusundaki eski reklam şablonu.',
    features: ['Arşiv'],
    usageSteps: ['Geri yükleyin veya kalıcı silin'],
    thumbUrl: THUMBS[3]!,
    gallery: galleryFrom(3),
    builderHref: builderFor('ad'),
    colorHint: '#718087',
  },
];

export function filterTemplates(
  items: StudioTemplate[],
  opts: {
    category: TemplateType | 'all';
    source: TemplateSource | null;
    packId: TemplatePackId | null;
    query: string;
    typeFilter: TemplateType | 'all';
    deviceFilter: DeviceKind | 'all';
  },
): StudioTemplate[] {
  const q = opts.query.trim().toLowerCase();
  return items.filter((tpl) => {
    if (opts.source === 'trash') {
      if (!tpl.trashed) return false;
    } else if (tpl.trashed) {
      return false;
    }

    if (opts.source === 'favorites' && !tpl.favorite) return false;
    if (opts.source === 'recent' && !tpl.recentlyUsed) return false;
    if (opts.source === 'ai' && tpl.source !== 'ai') return false;
    if (opts.source === 'company' && tpl.source !== 'company') return false;
    if (opts.source === 'personal' && tpl.source !== 'personal') return false;

    if (opts.packId && tpl.packId !== opts.packId) return false;

    if (opts.category !== 'all' && tpl.type !== opts.category) return false;
    if (opts.typeFilter !== 'all' && tpl.type !== opts.typeFilter) return false;
    if (opts.deviceFilter !== 'all' && !tpl.devices.includes(opts.deviceFilter)) return false;

    if (!q) return true;
    const hay = `${tpl.name} ${tpl.categoryLabel} ${tpl.tags.join(' ')} ${tpl.description}`.toLowerCase();
    return hay.includes(q);
  });
}

export function sortTemplates(items: StudioTemplate[], sort: SortKey): StudioTemplate[] {
  const next = [...items];
  if (sort === 'popular') next.sort((a, b) => b.popularScore - a.popularScore);
  else if (sort === 'newest') next.sort((a, b) => a.id < b.id ? 1 : -1);
  else next.sort((a, b) => a.name.localeCompare(b.name, 'tr'));
  return next;
}
