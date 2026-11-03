import {
  getCreativeStudioMediaContentUrl,
  type CreativeStudioMediaAsset,
} from '@/lib/api/creative-studio';
import type { LocationIntelligenceResponse, MetricValue, Project } from '@/lib/api/projects';
import {
  heroRank,
  isOperationalProjectMedia,
  projectMediaCategory,
} from '@/lib/projects/project-gallery-media';

import {
  emptyLocation,
  emptyMediaStats,
  type FloorPlanItem,
  type LocationIntelligence,
  type MediaStats,
  type ProjectGalleryItem,
  type AmenityCategory,
  type AmenityItem,
} from './projects-detail-media-model';

export type OverviewDocument = {
  id: string;
  title: string;
  documentType: string;
  folder: string;
  fileKind: string;
  mimeType: string;
  updatedAt: string;
  uploadedByName: string;
  documentDate: string | null;
  tags: string;
};

function text(value: unknown): string {
  return typeof value === 'string' ? value : '';
}

export function readOverviewDocument(raw: Record<string, unknown>): OverviewDocument | null {
  const id = text(raw.id);
  if (!id) return null;
  return {
    id,
    title: text(raw.title) || text(raw.original_file_name) || id,
    documentType: text(raw.document_type),
    folder: text(raw.folder),
    fileKind: text(raw.file_kind),
    mimeType: text(raw.mime_type),
    updatedAt: text(raw.updated_at) || text(raw.created_at),
    uploadedByName: text(raw.uploaded_by_name),
    documentDate: text(raw.document_date) || null,
    tags: text(raw.tags),
  };
}

function isImageAsset(asset: CreativeStudioMediaAsset): boolean {
  return asset.content_type.toLowerCase().startsWith('image/');
}

function isVideoAsset(asset: CreativeStudioMediaAsset): boolean {
  return asset.content_type.toLowerCase().startsWith('video/');
}

function toGalleryItem(asset: CreativeStudioMediaAsset): ProjectGalleryItem {
  const title = asset.filename || asset.id;
  const category = projectMediaCategory(asset);
  return {
    id: asset.id,
    category: category as ProjectGalleryItem['category'],
    titleEn: title,
    titleTr: title,
    uploadedAt: (asset.updated_at || asset.created_at || '').slice(0, 10),
    photographer: asset.source_type === 'google_drive' ? 'Google Drive' : 'Upload',
    source: asset.folder_category || asset.content_type,
    imageUrl: isImageAsset(asset)
      ? getCreativeStudioMediaContentUrl(asset.id, { linked_project_id: asset.linked_project_id })
      : null,
    scene: 'plaza',
    accent: 0,
  };
}

export type OverviewMedia = {
  heroImageUrl: string | null;
  gallery: ProjectGalleryItem[];
  constructionPhotos: ProjectGalleryItem[];
  floorPlans: FloorPlanItem[];
  permits: Array<{ id: string; title: string; date: string | null }>;
  mediaStats: MediaStats;
  location: LocationIntelligence;
};

export function buildOverviewMedia(
  project: Project | null,
  assets: CreativeStudioMediaAsset[],
): OverviewMedia {
  const projectId = project?.id ?? null;
  const gallery = assets
    .filter((asset) => (projectId ? asset.linked_project_id === projectId : false))
    .filter((asset) => isOperationalProjectMedia(asset))
    .map(toGalleryItem)
    .sort((a, b) => heroRank(a.category) - heroRank(b.category) || a.titleEn.localeCompare(b.titleEn));
  const hero = gallery.find((item) => item.imageUrl) ?? null;
  const latest = gallery
    .map((item) => item.uploadedAt)
    .filter(Boolean)
    .sort()
    .at(-1);
  const floorPlans = gallery.filter((item) => item.category === 'floorPlan');

  const address = [project?.address, project?.city, project?.state, project?.country].filter(Boolean).join(', ');

  return {
    heroImageUrl: hero?.imageUrl ?? null,
    gallery,
    constructionPhotos: gallery.filter((item) => item.category === 'construction'),
    floorPlans: floorPlans.map((item) => ({
      id: item.id,
      type: null,
      label: item.titleEn,
      areaSqm: null,
      unitCount: null,
      pdfUrl: '',
      imageUrl: item.imageUrl,
      scene: 'plaza' as const,
      accent: 0,
    })),
    permits: [],
    mediaStats: {
      ...emptyMediaStats(),
      photos: gallery.filter((item) => Boolean(item.imageUrl)).length,
      videos: assets.filter(
        (asset) =>
          asset.linked_project_id === projectId &&
          isOperationalProjectMedia(asset) &&
          isVideoAsset(asset),
      ).length,
      drone: gallery.filter((item) => item.category === 'drone').length,
      renderings: gallery.filter(
        (item) =>
          item.category === 'rendering' ||
          item.category === 'exterior' ||
          item.category === 'interior',
      ).length,
      floorPlans: floorPlans.length,
      documents: 0,
      lastUpdated: latest ?? '',
    },
    location: {
      ...emptyLocation(),
      addressEn: address,
      addressTr: address,
    },
  };
}

export function metricText(metric: MetricValue | null | undefined, locale: string): string | null {
  if (!metric?.available || metric.value == null || metric.value === '') return null;
  const amount = Number(metric.value);
  if (!Number.isFinite(amount)) return null;
  return new Intl.NumberFormat(locale === 'tr' ? 'tr-TR' : 'en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(amount);
}

const AMENITY_CATEGORIES = new Set<AmenityCategory>([
  'food',
  'grocery',
  'parks',
  'fitness',
  'education',
  'healthcare',
  'transit',
  'retail',
  'landmarks',
]);

export function overlayLocationIntelligence(
  location: LocationIntelligence,
  intel: LocationIntelligenceResponse | null,
): { location: LocationIntelligence; amenities: AmenityItem[] } {
  const verified = intel?.status === 'success' && intel.latitude != null && intel.longitude != null;
  if (!intel || !verified) {
    return {
      location: {
        ...location,
        lat: null,
        lng: null,
        neighborhoodEn: '',
        neighborhoodTr: '',
        aiSummary: null,
        canRefresh: Boolean(intel?.can_refresh),
        refreshedAt: intel?.refreshed_at ?? null,
        nearbyPlaces: [],
      },
      amenities: [],
    };
  }
  const identity = intel.neighborhood || intel.locality || '';
  const places = intel.nearby_places.filter((place) => AMENITY_CATEGORIES.has(place.category as AmenityCategory));
  return {
    location: {
      ...location,
      lat: intel.latitude,
      lng: intel.longitude,
      addressEn: intel.formatted_address || location.addressEn,
      addressTr: intel.formatted_address || location.addressTr,
      neighborhoodEn: identity,
      neighborhoodTr: identity,
      overviewEn: '',
      overviewTr: '',
      aiSummary: intel.ai_summary?.summary_text ?? null,
      canRefresh: intel.can_refresh,
      refreshedAt: intel.refreshed_at,
      nearbyPlaces: places.map((place) => ({
        id: place.id,
        nameEn: place.name,
        nameTr: place.name,
        kindEn: place.category,
        kindTr: place.category,
        distanceKm: place.straight_line_distance_meters / 1000,
        lat: place.latitude,
        lng: place.longitude,
        address: place.address,
      })),
    },
    amenities: places.map((place) => ({
      id: place.id,
      category: place.category as AmenityCategory,
      nameEn: place.name,
      nameTr: place.name,
      distanceKm: place.straight_line_distance_meters / 1000,
      walkMin: place.walking_duration_minutes,
      driveMin: null,
      rating: place.rating,
    })),
  };
}
