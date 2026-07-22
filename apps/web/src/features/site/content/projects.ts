export type SiteProjectStatus = 'coming_soon' | 'selling' | 'completed';

export type SiteProject = {
  slug: string;
  name: { en: string; tr: string };
  location: { en: string; tr: string };
  city: string;
  status: SiteProjectStatus;
  summary: { en: string; tr: string };
  investmentSummary: { en: string; tr: string };
  highlights: { en: string[]; tr: string[] };
  amenities: { en: string[]; tr: string[] };
  floorPlans: { id: string; label: { en: string; tr: string }; areaM2: number; rooms: string }[];
  downloads: { id: string; label: { en: string; tr: string }; href: string; available: boolean }[];
  gallery: { id: string; alt: { en: string; tr: string }; tone: 'warm' | 'cool' | 'neutral' }[];
  coords: { lat: number; lng: number };
  metrics: {
    units?: number;
    projectedYield?: string;
    minTicket?: string;
  };
  featured?: boolean;
};

/**
 * Public catalog placeholders until a published public projects API exists.
 * Structure mirrors expected CMS/API fields for a clean swap later.
 */
export const SITE_PROJECTS: SiteProject[] = [
  {
    slug: 'marina-residences',
    name: { en: 'Marina Residences', tr: 'Marina Residences' },
    location: { en: 'Kadıköy waterfront, Istanbul', tr: 'Kadıköy sahil, İstanbul' },
    city: 'Istanbul',
    status: 'selling',
    featured: true,
    summary: {
      en: 'Waterfront residences designed for long-term yield and lifestyle demand.',
      tr: 'Uzun vadeli getiri ve yaşam talebi için tasarlanmış sahil residansları.',
    },
    investmentSummary: {
      en: 'Balanced ticket sizes with rental-ready finishes and strong local demand drivers.',
      tr: 'Kiralama hazır bitişler ve güçlü yerel talep ile dengeli yatırım paketleri.',
    },
    highlights: {
      en: ['Sea-facing units', 'Rental-ready delivery', 'Managed common areas'],
      tr: ['Deniz manzaralı üniteler', 'Kiralamaya hazır teslim', 'Yönetimli ortak alanlar'],
    },
    amenities: {
      en: ['Concierge', 'Fitness', 'Rooftop lounge', 'Secure parking'],
      tr: ['Concierge', 'Fitness', 'Çatı lounge', 'Güvenli otopark'],
    },
    floorPlans: [
      { id: '1plus1', label: { en: '1+1 Residence', tr: '1+1 Residans' }, areaM2: 68, rooms: '1+1' },
      { id: '2plus1', label: { en: '2+1 Residence', tr: '2+1 Residans' }, areaM2: 112, rooms: '2+1' },
      { id: '3plus1', label: { en: '3+1 Residence', tr: '3+1 Residans' }, areaM2: 148, rooms: '3+1' },
    ],
    downloads: [
      { id: 'brochure', label: { en: 'Project brochure (PDF)', tr: 'Proje broşürü (PDF)' }, href: '/lead/brochure?project=marina-residences', available: true },
      { id: 'floorplans', label: { en: 'Floor plan pack', tr: 'Kat planı paketi' }, href: '/lead/brochure?project=marina-residences', available: true },
    ],
    gallery: [
      { id: 'g1', alt: { en: 'Marina facade dusk', tr: 'Marina cephe akşam' }, tone: 'cool' },
      { id: 'g2', alt: { en: 'Lobby interior', tr: 'Lobi iç mekan' }, tone: 'warm' },
      { id: 'g3', alt: { en: 'Terrace view', tr: 'Teras manzarası' }, tone: 'neutral' },
    ],
    coords: { lat: 40.9905, lng: 29.0292 },
    metrics: { units: 186, projectedYield: '6.5–8.0%', minTicket: 'from €185k' },
  },
  {
    slug: 'anatolia-business-hub',
    name: { en: 'Anatolia Business Hub', tr: 'Anadolu İş Merkezi' },
    location: { en: 'Çankaya, Ankara', tr: 'Çankaya, Ankara' },
    city: 'Ankara',
    status: 'selling',
    featured: true,
    summary: {
      en: 'Grade-A office floors positioned for institutional and SME tenants.',
      tr: 'Kurumsal ve KOBİ kiracılar için konumlanmış A sınıfı ofis katları.',
    },
    investmentSummary: {
      en: 'Income-focused product with flexible floor plates and transport access.',
      tr: 'Esnek kat planları ve ulaşım erişimi ile gelir odaklı ürün.',
    },
    highlights: {
      en: ['LEED-ready envelope', 'Flexible plates', 'Metro adjacency'],
      tr: ['LEED hazır kabuk', 'Esnek katlar', 'Metro yakınlığı'],
    },
    amenities: {
      en: ['Conference center', 'Cafe court', 'EV charging', '24/7 security'],
      tr: ['Konferans merkezi', 'Cafe alanı', 'EV şarj', '7/24 güvenlik'],
    },
    floorPlans: [
      { id: 'plate-a', label: { en: 'Open plate A', tr: 'Açık plan A' }, areaM2: 420, rooms: 'Open' },
      { id: 'plate-b', label: { en: 'Open plate B', tr: 'Açık plan B' }, areaM2: 610, rooms: 'Open' },
    ],
    downloads: [
      { id: 'brochure', label: { en: 'Investment brief', tr: 'Yatırım özeti' }, href: '/lead/analysis?project=anatolia-business-hub', available: true },
    ],
    gallery: [
      { id: 'g1', alt: { en: 'Tower exterior', tr: 'Kule dış görünüm' }, tone: 'neutral' },
      { id: 'g2', alt: { en: 'Floor plate', tr: 'Kat planı' }, tone: 'cool' },
    ],
    coords: { lat: 39.9106, lng: 32.8541 },
    metrics: { units: 48, projectedYield: '7.0–9.0%', minTicket: 'from €320k' },
  },
  {
    slug: 'aegean-villa-collection',
    name: { en: 'Aegean Villa Collection', tr: 'Ege Villa Koleksiyonu' },
    location: { en: 'Bodrum hills, Muğla', tr: 'Bodrum tepeleri, Muğla' },
    city: 'Bodrum',
    status: 'coming_soon',
    featured: true,
    summary: {
      en: 'Limited villa inventory with seasonal rental upside and second-home demand.',
      tr: 'Sezonluk kira potansiyeli ve ikinci konut talebiyle sınırlı villa stoku.',
    },
    investmentSummary: {
      en: 'Scarcity-led collection for investors seeking lifestyle assets with yield optionality.',
      tr: 'Getiri seçenekleri olan yaşam tarzı varlıkları arayan yatırımcılar için kıtlık odaklı koleksiyon.',
    },
    highlights: {
      en: ['Limited release', 'Private pools', 'Managed rental program'],
      tr: ['Sınırlı satış', 'Özel havuzlar', 'Yönetimli kiralama programı'],
    },
    amenities: {
      en: ['Spa pavilion', 'Helipad access nearby', 'Concierge'],
      tr: ['Spa pavyonu', 'Yakın helipad erişimi', 'Concierge'],
    },
    floorPlans: [
      { id: 'villa-a', label: { en: 'Villa Type A', tr: 'Villa Tip A' }, areaM2: 280, rooms: '4+1' },
      { id: 'villa-b', label: { en: 'Villa Type B', tr: 'Villa Tip B' }, areaM2: 360, rooms: '5+1' },
    ],
    downloads: [
      { id: 'waitlist', label: { en: 'Join waitlist pack', tr: 'Bekleme listesi paketi' }, href: '/lead/consultation?project=aegean-villa-collection', available: true },
    ],
    gallery: [
      { id: 'g1', alt: { en: 'Villa terrace dusk', tr: 'Villa teras akşam' }, tone: 'warm' },
      { id: 'g2', alt: { en: 'Pool court', tr: 'Havuz avlusu' }, tone: 'cool' },
    ],
    coords: { lat: 37.0344, lng: 27.4305 },
    metrics: { units: 22, projectedYield: '5.5–8.5%', minTicket: 'on request' },
  },
  {
    slug: 'bosphorus-completed',
    name: { en: 'Bosphorus Court', tr: 'Boğaz Court' },
    location: { en: 'Beşiktaş, Istanbul', tr: 'Beşiktaş, İstanbul' },
    city: 'Istanbul',
    status: 'completed',
    summary: {
      en: 'Delivered mixed-use court with stabilized occupancy — shown for trust and track record.',
      tr: 'Stabilize doluluk ile teslim edilmiş karma kullanım — güven ve referans için.',
    },
    investmentSummary: {
      en: 'Completed reference project demonstrating delivery discipline and tenant retention.',
      tr: 'Teslim disiplini ve kiracı tutma performansını gösteren tamamlanmış referans proje.',
    },
    highlights: {
      en: ['Delivered 2023', 'Stabilized occupancy', 'Retail podium'],
      tr: ['2023 teslim', 'Stabilize doluluk', 'Perakende podium'],
    },
    amenities: {
      en: ['Retail street', 'Courtyard', 'Bike storage'],
      tr: ['Perakende caddesi', 'Avlu', 'Bisiklet deposu'],
    },
    floorPlans: [],
    downloads: [],
    gallery: [{ id: 'g1', alt: { en: 'Completed courtyard', tr: 'Tamamlanmış avlu' }, tone: 'neutral' }],
    coords: { lat: 41.0422, lng: 29.0067 },
    metrics: { units: 94, projectedYield: 'stabilized', minTicket: '—' },
  },
];

export function getFeaturedProjects(): SiteProject[] {
  return SITE_PROJECTS.filter((p) => p.featured);
}

export function getProjectBySlug(slug: string): SiteProject | undefined {
  return SITE_PROJECTS.find((p) => p.slug === slug);
}

export function getProjectsByStatus(status: SiteProjectStatus): SiteProject[] {
  return SITE_PROJECTS.filter((p) => p.status === status);
}
