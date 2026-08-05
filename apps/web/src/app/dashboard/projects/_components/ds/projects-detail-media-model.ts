/**
 * Project Detail — Digital Twin media & location fixtures.
 * Structured for future Proposal Engine consumption (presentation-only).
 */

import { hashIndex, type CoverScene } from './projects-ds-model';

export type GalleryCategory =
  | 'cover'
  | 'exterior'
  | 'interior'
  | 'drone'
  | 'street'
  | 'marketing'
  | 'construction';

export type ProjectGalleryItem = {
  id: string;
  category: GalleryCategory;
  titleEn: string;
  titleTr: string;
  uploadedAt: string;
  photographer: string;
  source: string;
  scene: CoverScene;
  /** Visual accent index 0–5 for CSS scene variants */
  accent: number;
};

export type ConstructionPhaseKey =
  | 'foundation'
  | 'structure'
  | 'facade'
  | 'roof'
  | 'mep'
  | 'interior'
  | 'landscaping';

export type InspectionStatus = 'passed' | 'pending' | 'scheduled' | 'failed';

export type ConstructionMediaItem = {
  id: string;
  type: 'photo' | 'video';
  captionEn: string;
  captionTr: string;
  scene: CoverScene;
  accent: number;
};

export type ConstructionGalleryMilestone = {
  id: string;
  phase: ConstructionPhaseKey;
  date: string;
  progressPct: number;
  contractor: string;
  inspectionStatus: InspectionStatus;
  media: ConstructionMediaItem[];
};

export type FloorPlanType =
  | 'studio'
  | 'oneBr'
  | 'twoBr'
  | 'threeBr'
  | 'penthouse'
  | 'commercial'
  | 'storage'
  | 'garage';

export type FloorPlanItem = {
  id: string;
  type: FloorPlanType;
  areaSqm: number;
  unitCount: number;
  pdfUrl: string;
  scene: CoverScene;
  accent: number;
};

export type WalkScoreKind = 'walk' | 'transit' | 'bike';

export type WalkScoreBadgeKey =
  | 'walkersParadise'
  | 'veryWalkable'
  | 'somewhatWalkable'
  | 'carDependent'
  | 'excellentTransit'
  | 'goodTransit'
  | 'someTransit'
  | 'bikersParadise'
  | 'veryBikeable'
  | 'bikeable';

export type WalkScoreItem = {
  kind: WalkScoreKind;
  score: number;
  badge: WalkScoreBadgeKey;
  descriptionEn: string;
  descriptionTr: string;
};

export type AmenityCategory =
  | 'schools'
  | 'universities'
  | 'metro'
  | 'bus'
  | 'hospitals'
  | 'clinics'
  | 'shopping'
  | 'restaurants'
  | 'coffee'
  | 'parks'
  | 'fitness'
  | 'banks'
  | 'pharmacies'
  | 'entertainment'
  | 'government';

export type AmenityItem = {
  id: string;
  category: AmenityCategory;
  nameEn: string;
  nameTr: string;
  distanceKm: number;
  walkMin: number;
  driveMin: number;
  rating: number | null;
};

export type NearbyPlace = {
  id: string;
  nameEn: string;
  nameTr: string;
  kindEn: string;
  kindTr: string;
  distanceKm: number;
};

export type RadiusBand = {
  id: string;
  mode: 'walk' | 'drive';
  minutes: number;
};

export type LocationIntelligence = {
  lat: number;
  lng: number;
  addressEn: string;
  addressTr: string;
  neighborhoodEn: string;
  neighborhoodTr: string;
  overviewEn: string;
  overviewTr: string;
  nearbyPlaces: NearbyPlace[];
  radii: RadiusBand[];
};

export type MarketMetricKey =
  | 'medianSale'
  | 'medianRent'
  | 'appreciation'
  | 'rentalDemand'
  | 'inventory'
  | 'daysOnMarket'
  | 'neighborhoodGrowth';

export type MarketMetric = {
  key: MarketMetricKey;
  valueEn: string;
  valueTr: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
};

export type MarketIntelligence = {
  metrics: MarketMetric[];
};

export type MediaStats = {
  photos: number;
  videos: number;
  drone: number;
  renderings: number;
  floorPlans: number;
  documents: number;
  lastUpdated: string;
};

/** Full consumable bundle for Proposal Engine / Digital Twin Overview. */
export type ProjectProposalMediaBundle = {
  projectId: string;
  mediaStats: MediaStats;
  gallery: ProjectGalleryItem[];
  constructionGallery: ConstructionGalleryMilestone[];
  floorPlans: FloorPlanItem[];
  location: LocationIntelligence;
  walkScores: WalkScoreItem[];
  amenities: AmenityItem[];
  market: MarketIntelligence;
};

const SCENES: CoverScene[] = ['marina', 'tower', 'garden', 'coast', 'plaza', 'ridge'];

const PHOTOGRAPHERS = [
  'Studio Horizon Media',
  'Aerial TR Drone',
  'Site Progress Lab',
  'Marmara Visuals',
  'Investhome Capture',
];

const CONTRACTORS = [
  'Marmara İnşaat A.Ş.',
  'Ankara Yapı Group',
  'Ege Construction Co.',
  'Bosphorus Builders',
];

function sceneFor(seed: string): CoverScene {
  return SCENES[hashIndex(seed, SCENES.length)]!;
}

function dateOffset(daysAgo: number): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().slice(0, 10);
}

function walkBadge(score: number): WalkScoreBadgeKey {
  if (score >= 90) return 'walkersParadise';
  if (score >= 70) return 'veryWalkable';
  if (score >= 50) return 'somewhatWalkable';
  return 'carDependent';
}

function transitBadge(score: number): WalkScoreBadgeKey {
  if (score >= 80) return 'excellentTransit';
  if (score >= 60) return 'goodTransit';
  return 'someTransit';
}

function bikeBadge(score: number): WalkScoreBadgeKey {
  if (score >= 90) return 'bikersParadise';
  if (score >= 70) return 'veryBikeable';
  return 'bikeable';
}

export function localizedTitle(
  item: { titleEn: string; titleTr: string },
  locale: string,
): string {
  return locale === 'tr' ? item.titleTr : item.titleEn;
}

export function localizedName(
  item: { nameEn: string; nameTr: string },
  locale: string,
): string {
  return locale === 'tr' ? item.nameTr : item.nameEn;
}

export function localizedCaption(
  item: { captionEn: string; captionTr: string },
  locale: string,
): string {
  return locale === 'tr' ? item.captionTr : item.captionEn;
}

export function localizedValue(
  item: { valueEn: string; valueTr: string },
  locale: string,
): string {
  return locale === 'tr' ? item.valueTr : item.valueEn;
}

function buildGallery(projectId: string): ProjectGalleryItem[] {
  const entries: Array<{
    category: GalleryCategory;
    titleEn: string;
    titleTr: string;
    daysAgo: number;
  }> = [
    { category: 'cover', titleEn: 'Hero cover — dusk elevation', titleTr: 'Kapak — alacakaranlık cephe', daysAgo: 12 },
    { category: 'cover', titleEn: 'Entry plaza cover', titleTr: 'Giriş plazası kapak', daysAgo: 18 },
    { category: 'exterior', titleEn: 'North façade rendering', titleTr: 'Kuzey cephe render', daysAgo: 40 },
    { category: 'exterior', titleEn: 'Garden court exterior', titleTr: 'Bahçe avlusu dış görünüm', daysAgo: 42 },
    { category: 'exterior', titleEn: 'Street-facing podium', titleTr: 'Sokak cepheli podium', daysAgo: 55 },
    { category: 'interior', titleEn: 'Lobby atrium render', titleTr: 'Lobi atrium render', daysAgo: 28 },
    { category: 'interior', titleEn: 'Living room — 2BR sample', titleTr: 'Oturma odası — 2+1 örnek', daysAgo: 30 },
    { category: 'interior', titleEn: 'Kitchen & dining suite', titleTr: 'Mutfak ve yemek alanı', daysAgo: 33 },
    { category: 'drone', titleEn: 'Drone flyover — Q2', titleTr: 'Drone uçuşu — Q2', daysAgo: 8 },
    { category: 'drone', titleEn: 'Site context aerial', titleTr: 'Saha bağlamı havadan', daysAgo: 15 },
    { category: 'street', titleEn: 'Street view — main approach', titleTr: 'Sokak görünümü — ana yaklaşım', daysAgo: 22 },
    { category: 'street', titleEn: 'Corner intersection context', titleTr: 'Köşe kavşak bağlamı', daysAgo: 25 },
    { category: 'marketing', titleEn: 'Lifestyle amenity deck', titleTr: 'Yaşam alanı amenite terası', daysAgo: 35 },
    { category: 'marketing', titleEn: 'Sunset brand still', titleTr: 'Gün batımı marka karesi', daysAgo: 38 },
    { category: 'construction', titleEn: 'Tower core progress', titleTr: 'Kule çekirdek ilerlemesi', daysAgo: 5 },
    { category: 'construction', titleEn: 'Façade sample install', titleTr: 'Cephe örnek montajı', daysAgo: 9 },
  ];

  return entries.map((e, i) => ({
    id: `${projectId}-gal-${i}`,
    category: e.category,
    titleEn: e.titleEn,
    titleTr: e.titleTr,
    uploadedAt: dateOffset(e.daysAgo),
    photographer: PHOTOGRAPHERS[hashIndex(`${projectId}-ph-${i}`, PHOTOGRAPHERS.length)]!,
    source: e.category === 'drone' ? 'Aerial TR Drone' : 'Project Media Library',
    scene: sceneFor(`${projectId}-gal-${e.category}-${i}`),
    accent: hashIndex(`${projectId}-acc-${i}`, 6),
  }));
}

function buildConstructionGallery(projectId: string): ConstructionGalleryMilestone[] {
  const phases: Array<{
    phase: ConstructionPhaseKey;
    progressPct: number;
    daysAgo: number;
    inspection: InspectionStatus;
  }> = [
    { phase: 'foundation', progressPct: 100, daysAgo: 210, inspection: 'passed' },
    { phase: 'structure', progressPct: 92, daysAgo: 120, inspection: 'passed' },
    { phase: 'facade', progressPct: 68, daysAgo: 45, inspection: 'scheduled' },
    { phase: 'roof', progressPct: 55, daysAgo: 38, inspection: 'pending' },
    { phase: 'mep', progressPct: 48, daysAgo: 30, inspection: 'pending' },
    { phase: 'interior', progressPct: 32, daysAgo: 18, inspection: 'scheduled' },
    { phase: 'landscaping', progressPct: 12, daysAgo: 10, inspection: 'pending' },
  ];

  return phases.map((p, i) => {
    const contractor = CONTRACTORS[hashIndex(`${projectId}-c-${i}`, CONTRACTORS.length)]!;
    return {
      id: `${projectId}-cg-${p.phase}`,
      phase: p.phase,
      date: dateOffset(p.daysAgo),
      progressPct: p.progressPct,
      contractor,
      inspectionStatus: p.inspection,
      media: [
        {
          id: `${projectId}-cg-${p.phase}-p0`,
          type: 'photo' as const,
          captionEn: `${p.phase} progress still`,
          captionTr: `${p.phase} ilerleme karesi`,
          scene: sceneFor(`${projectId}-cg-${p.phase}-0`),
          accent: hashIndex(`${projectId}-cg-a-${i}`, 6),
        },
        {
          id: `${projectId}-cg-${p.phase}-p1`,
          type: i % 3 === 0 ? ('video' as const) : ('photo' as const),
          captionEn: i % 3 === 0 ? 'Time-lapse clip' : 'Detail inspection frame',
          captionTr: i % 3 === 0 ? 'Hızlandırılmış klip' : 'Detay denetim karesi',
          scene: sceneFor(`${projectId}-cg-${p.phase}-1`),
          accent: hashIndex(`${projectId}-cg-b-${i}`, 6),
        },
      ],
    };
  });
}

function buildFloorPlans(projectId: string): FloorPlanItem[] {
  const plans: Array<{ type: FloorPlanType; areaSqm: number; unitCount: number }> = [
    { type: 'studio', areaSqm: 42, unitCount: 18 },
    { type: 'oneBr', areaSqm: 68, unitCount: 42 },
    { type: 'twoBr', areaSqm: 98, unitCount: 56 },
    { type: 'threeBr', areaSqm: 132, unitCount: 28 },
    { type: 'penthouse', areaSqm: 245, unitCount: 4 },
    { type: 'commercial', areaSqm: 180, unitCount: 6 },
    { type: 'storage', areaSqm: 8, unitCount: 64 },
    { type: 'garage', areaSqm: 14, unitCount: 120 },
  ];

  return plans.map((p, i) => ({
    id: `${projectId}-fp-${p.type}`,
    type: p.type,
    areaSqm: p.areaSqm,
    unitCount: p.unitCount,
    pdfUrl: `#floor-plan-${p.type}`,
    scene: sceneFor(`${projectId}-fp-${i}`),
    accent: hashIndex(`${projectId}-fp-a-${i}`, 6),
  }));
}

function buildLocation(projectId: string): LocationIntelligence {
  const latBase = 41.0082 + (hashIndex(projectId, 80) - 40) * 0.002;
  const lngBase = 28.9784 + (hashIndex(`${projectId}-lng`, 80) - 40) * 0.002;
  return {
    lat: Number(latBase.toFixed(5)),
    lng: Number(lngBase.toFixed(5)),
    addressEn: 'Caddebostan Sahil Yolu 48, Kadıköy, İstanbul',
    addressTr: 'Caddebostan Sahil Yolu 48, Kadıköy, İstanbul',
    neighborhoodEn: 'Caddebostan · Asian Side',
    neighborhoodTr: 'Caddebostan · Anadolu Yakası',
    overviewEn:
      'Waterfront residential pocket with mature tree canopy, strong retail frontage, and direct coastal promenade access.',
    overviewTr:
      'Olgun ağaç örtüsü, güçlü perakende cephesi ve doğrudan sahil yürüyüş yolu erişimi olan kıyı konut bölgesi.',
    nearbyPlaces: [
      {
        id: `${projectId}-np-1`,
        nameEn: 'Caddebostan Pier',
        nameTr: 'Caddebostan İskelesi',
        kindEn: 'Waterfront',
        kindTr: 'Sahil',
        distanceKm: 0.4,
      },
      {
        id: `${projectId}-np-2`,
        nameEn: 'Bağdat Avenue',
        nameTr: 'Bağdat Caddesi',
        kindEn: 'Retail corridor',
        kindTr: 'Perakende koridoru',
        distanceKm: 0.6,
      },
      {
        id: `${projectId}-np-3`,
        nameEn: 'Göztepe Park',
        nameTr: 'Göztepe Parkı',
        kindEn: 'Park',
        kindTr: 'Park',
        distanceKm: 1.1,
      },
      {
        id: `${projectId}-np-4`,
        nameEn: 'Kadıköy Ferry Hub',
        nameTr: 'Kadıköy Vapur İskelesi',
        kindEn: 'Transit',
        kindTr: 'Ulaşım',
        distanceKm: 3.2,
      },
    ],
    radii: [
      { id: 'w5', mode: 'walk', minutes: 5 },
      { id: 'w15', mode: 'walk', minutes: 15 },
      { id: 'd10', mode: 'drive', minutes: 10 },
      { id: 'd20', mode: 'drive', minutes: 20 },
    ],
  };
}

function buildWalkScores(projectId: string): WalkScoreItem[] {
  const walk = 88 + hashIndex(projectId, 10);
  const transit = 72 + hashIndex(`${projectId}-t`, 18);
  const bike = 78 + hashIndex(`${projectId}-b`, 16);
  return [
    {
      kind: 'walk',
      score: Math.min(99, walk),
      badge: walkBadge(walk),
      descriptionEn: 'Daily needs are within a short walk along Bağdat Avenue and the coastal strip.',
      descriptionTr: 'Günlük ihtiyaçlar Bağdat Caddesi ve sahil şeridinde kısa yürüyüş mesafesinde.',
    },
    {
      kind: 'transit',
      score: Math.min(98, transit),
      badge: transitBadge(transit),
      descriptionEn: 'Metrobus, metro feeders, and ferry connections cover cross-city commuting.',
      descriptionTr: 'Metrobüs, metro bağlantıları ve vapur hatları şehirler arası ulaşımı kapsar.',
    },
    {
      kind: 'bike',
      score: Math.min(98, bike),
      badge: bikeBadge(bike),
      descriptionEn: 'Flat coastal bike lanes and neighborhood routes support everyday cycling.',
      descriptionTr: 'Düz sahil bisiklet yolları ve mahalle rotaları günlük bisiklet kullanımını destekler.',
    },
  ];
}

function buildAmenities(projectId: string): AmenityItem[] {
  const rows: Array<{
    category: AmenityCategory;
    nameEn: string;
    nameTr: string;
    distanceKm: number;
    walkMin: number;
    driveMin: number;
    rating: number | null;
  }> = [
    { category: 'schools', nameEn: 'Kadıköy Anatolian High School', nameTr: 'Kadıköy Anadolu Lisesi', distanceKm: 1.2, walkMin: 15, driveMin: 5, rating: 4.6 },
    { category: 'universities', nameEn: 'Marmara University Campus', nameTr: 'Marmara Üniversitesi Kampüsü', distanceKm: 2.8, walkMin: 34, driveMin: 9, rating: 4.4 },
    { category: 'metro', nameEn: 'Göztepe Metro Station', nameTr: 'Göztepe Metro İstasyonu', distanceKm: 1.5, walkMin: 18, driveMin: 6, rating: 4.5 },
    { category: 'bus', nameEn: 'Caddebostan Bus Hub', nameTr: 'Caddebostan Otobüs Durağı', distanceKm: 0.3, walkMin: 4, driveMin: 2, rating: 4.2 },
    { category: 'hospitals', nameEn: 'Acıbadem Kadıköy Hospital', nameTr: 'Acıbadem Kadıköy Hastanesi', distanceKm: 2.1, walkMin: 26, driveMin: 8, rating: 4.7 },
    { category: 'clinics', nameEn: 'Family Health Clinic', nameTr: 'Aile Sağlığı Merkezi', distanceKm: 0.7, walkMin: 9, driveMin: 3, rating: 4.3 },
    { category: 'shopping', nameEn: 'Optimum Outlet / Bağdat Retail', nameTr: 'Optimum / Bağdat Perakende', distanceKm: 3.4, walkMin: 42, driveMin: 11, rating: 4.5 },
    { category: 'restaurants', nameEn: 'Coastal Dining Row', nameTr: 'Sahil Restoran Sıra', distanceKm: 0.5, walkMin: 6, driveMin: 3, rating: 4.6 },
    { category: 'coffee', nameEn: 'Espresso Lab Caddebostan', nameTr: 'Espresso Lab Caddebostan', distanceKm: 0.4, walkMin: 5, driveMin: 2, rating: 4.8 },
    { category: 'parks', nameEn: 'Caddebostan Coastal Park', nameTr: 'Caddebostan Sahil Parkı', distanceKm: 0.35, walkMin: 4, driveMin: 2, rating: 4.7 },
    { category: 'fitness', nameEn: 'Macfit / Local Gym Cluster', nameTr: 'Macfit / Yerel Spor', distanceKm: 0.9, walkMin: 11, driveMin: 4, rating: 4.4 },
    { category: 'banks', nameEn: 'İş Bankası Branch', nameTr: 'İş Bankası Şubesi', distanceKm: 0.6, walkMin: 7, driveMin: 3, rating: 4.1 },
    { category: 'pharmacies', nameEn: 'Eczane Caddebostan', nameTr: 'Eczane Caddebostan', distanceKm: 0.25, walkMin: 3, driveMin: 2, rating: 4.5 },
    { category: 'entertainment', nameEn: 'Cinema & Cultural Hall', nameTr: 'Sinema ve Kültür Salonu', distanceKm: 1.8, walkMin: 22, driveMin: 7, rating: 4.3 },
    { category: 'government', nameEn: 'Kadıköy District Office', nameTr: 'Kadıköy Kaymakamlığı', distanceKm: 3.0, walkMin: 38, driveMin: 12, rating: null },
  ];

  return rows.map((r, i) => ({
    id: `${projectId}-am-${i}`,
    ...r,
  }));
}

function buildMarket(projectId: string): MarketIntelligence {
  const seed = hashIndex(projectId, 9);
  return {
    metrics: [
      {
        key: 'medianSale',
        valueEn: `$${(420 + seed * 12).toLocaleString('en-US')}/sqft`,
        valueTr: `$${(420 + seed * 12).toLocaleString('tr-TR')}/ft²`,
        delta: '+4.2%',
        deltaTone: 'up',
      },
      {
        key: 'medianRent',
        valueEn: `$${(18 + seed).toLocaleString('en-US')}/sqft`,
        valueTr: `$${(18 + seed).toLocaleString('tr-TR')}/ft²`,
        delta: '+2.1%',
        deltaTone: 'up',
      },
      {
        key: 'appreciation',
        valueEn: `${6.5 + seed * 0.3}% YoY`,
        valueTr: `%${(6.5 + seed * 0.3).toFixed(1)} Yıllık`,
        delta: '+0.8 pts',
        deltaTone: 'up',
      },
      {
        key: 'rentalDemand',
        valueEn: 'High',
        valueTr: 'Yüksek',
        delta: 'Stable',
        deltaTone: 'neutral',
      },
      {
        key: 'inventory',
        valueEn: `${2.4 + seed * 0.1} mo`,
        valueTr: `${(2.4 + seed * 0.1).toFixed(1)} ay`,
        delta: '-0.3 mo',
        deltaTone: 'down',
      },
      {
        key: 'daysOnMarket',
        valueEn: `${28 + seed} days`,
        valueTr: `${28 + seed} gün`,
        delta: '-5 days',
        deltaTone: 'down',
      },
      {
        key: 'neighborhoodGrowth',
        valueEn: `${3.8 + seed * 0.2}%`,
        valueTr: `%${(3.8 + seed * 0.2).toFixed(1)}`,
        delta: '+1.1%',
        deltaTone: 'up',
      },
    ],
  };
}

function buildMediaStats(
  gallery: ProjectGalleryItem[],
  construction: ConstructionGalleryMilestone[],
  floorPlans: FloorPlanItem[],
): MediaStats {
  const constructionPhotos = construction.reduce((n, m) => n + m.media.filter((x) => x.type === 'photo').length, 0);
  const constructionVideos = construction.reduce((n, m) => n + m.media.filter((x) => x.type === 'video').length, 0);
  const drone = gallery.filter((g) => g.category === 'drone').length;
  const renderings = gallery.filter((g) => g.category === 'exterior' || g.category === 'interior').length;
  const photos = gallery.length + constructionPhotos;
  return {
    photos,
    videos: constructionVideos + 2,
    drone,
    renderings,
    floorPlans: floorPlans.length,
    documents: 24,
    lastUpdated: dateOffset(2),
  };
}

/**
 * Returns a structured Digital Twin media bundle for a project.
 * Stable per projectId — suitable for Proposal Engine auto-assembly.
 */
export function getProjectProposalMediaBundle(projectId: string): ProjectProposalMediaBundle {
  const gallery = buildGallery(projectId);
  const constructionGallery = buildConstructionGallery(projectId);
  const floorPlans = buildFloorPlans(projectId);
  return {
    projectId,
    mediaStats: buildMediaStats(gallery, constructionGallery, floorPlans),
    gallery,
    constructionGallery,
    floorPlans,
    location: buildLocation(projectId),
    walkScores: buildWalkScores(projectId),
    amenities: buildAmenities(projectId),
    market: buildMarket(projectId),
  };
}

/** Module keys the Proposal Engine can request without manual selection. */
export const PROPOSAL_MEDIA_MODULE_KEYS = [
  'mediaStats',
  'gallery',
  'constructionGallery',
  'floorPlans',
  'location',
  'walkScores',
  'amenities',
  'market',
] as const;

export type ProposalMediaModuleKey = (typeof PROPOSAL_MEDIA_MODULE_KEYS)[number];
