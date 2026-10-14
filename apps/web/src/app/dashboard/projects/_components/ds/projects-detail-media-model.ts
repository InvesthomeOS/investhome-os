/**
 * Project Detail — Digital Twin media & location fixtures.
 * Structured for future Proposal Engine consumption (presentation-only).
 */

import type { CoverScene } from './projects-ds-model';

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
  imageUrl?: string | null;
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
  imageUrl?: string | null;
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
  type: FloorPlanType | null;
  label: string;
  areaSqm: number | null;
  unitCount: number | null;
  pdfUrl: string;
  imageUrl?: string | null;
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
  | 'food'
  | 'grocery'
  | 'parks'
  | 'fitness'
  | 'education'
  | 'healthcare'
  | 'transit'
  | 'retail'
  | 'landmarks'
  | 'schools'
  | 'universities'
  | 'metro'
  | 'bus'
  | 'hospitals'
  | 'clinics'
  | 'shopping'
  | 'restaurants'
  | 'coffee'
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
  walkMin: number | null;
  driveMin: number | null;
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
  lat: number | null;
  lng: number | null;
  addressEn: string;
  addressTr: string;
  neighborhoodEn: string;
  neighborhoodTr: string;
  overviewEn: string;
  overviewTr: string;
  nearbyPlaces: NearbyPlace[];
  radii: RadiusBand[];
  aiSummary: string | null;
  canRefresh: boolean;
  refreshedAt: string | null;
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

export function emptyLocation(): LocationIntelligence {
  return {
    lat: null,
    lng: null,
    addressEn: '',
    addressTr: '',
    neighborhoodEn: '',
    neighborhoodTr: '',
    overviewEn: '',
    overviewTr: '',
    nearbyPlaces: [],
    radii: [],
    aiSummary: null,
    canRefresh: false,
    refreshedAt: null,
  };
}

export function emptyMediaStats(): MediaStats {
  return {
    photos: 0,
    videos: 0,
    drone: 0,
    renderings: 0,
    floorPlans: 0,
    documents: 0,
    lastUpdated: '',
  };
}

/** Empty bundle. The overview fills sections from stored project records. */
export function getProjectProposalMediaBundle(projectId: string): ProjectProposalMediaBundle {
  return {
    projectId,
    mediaStats: emptyMediaStats(),
    gallery: [],
    constructionGallery: [],
    floorPlans: [],
    location: emptyLocation(),
    walkScores: [],
    amenities: [],
    market: { metrics: [] },
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
