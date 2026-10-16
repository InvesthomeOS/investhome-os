import { documentPreviewUrl } from '@/lib/api/documents';
import type { LocationIntelligenceResponse, MetricValue, Project } from '@/lib/api/projects';

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

const GALLERY_TYPES = new Set(['photo', 'image', 'video', 'marketing_material']);
const DRAWING_TYPES = new Set(['architectural_drawing', 'construction_drawing']);
const PERMIT_TYPES = new Set(['permit', 'inspection']);

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

function isImage(doc: OverviewDocument): boolean {
  return doc.fileKind === 'image' || doc.mimeType.startsWith('image/');
}

function isVideo(doc: OverviewDocument): boolean {
  return doc.documentType === 'video' || doc.fileKind === 'video' || doc.mimeType.startsWith('video/');
}

function galleryCategory(doc: OverviewDocument): ProjectGalleryItem['category'] {
  if (doc.documentType === 'marketing_material' || doc.folder === 'marketing') return 'marketing';
  if (doc.folder === 'construction') return 'construction';
  return 'cover';
}

function toGalleryItem(doc: OverviewDocument): ProjectGalleryItem {
  return {
    id: doc.id,
    category: galleryCategory(doc),
    titleEn: doc.title,
    titleTr: doc.title,
    uploadedAt: (doc.documentDate || doc.updatedAt).slice(0, 10),
    photographer: doc.uploadedByName,
    source: doc.documentType,
    imageUrl: isImage(doc) ? documentPreviewUrl(doc.id) : null,
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

export function buildOverviewMedia(project: Project | null, documents: OverviewDocument[]): OverviewMedia {
  const galleryDocs = documents.filter((doc) => GALLERY_TYPES.has(doc.documentType));
  const drawingDocs = documents.filter((doc) => DRAWING_TYPES.has(doc.documentType));
  const constructionDocs = documents.filter(
    (doc) => doc.folder === 'construction' && (GALLERY_TYPES.has(doc.documentType) || isImage(doc) || isVideo(doc)),
  );
  const permitDocs = documents.filter((doc) => PERMIT_TYPES.has(doc.documentType));
  const gallery = galleryDocs.map(toGalleryItem);
  const hero = galleryDocs.find(isImage) ?? null;
  const latest = documents
    .map((doc) => doc.updatedAt)
    .filter(Boolean)
    .sort()
    .at(-1);

  const address = [project?.address, project?.city, project?.state, project?.country].filter(Boolean).join(', ');

  return {
    heroImageUrl: hero ? documentPreviewUrl(hero.id) : null,
    gallery,
    constructionPhotos: constructionDocs.map(toGalleryItem),
    floorPlans: drawingDocs.map((doc) => ({
      id: doc.id,
      type: null,
      label: doc.title,
      areaSqm: null,
      unitCount: null,
      pdfUrl: documentPreviewUrl(doc.id),
      imageUrl: isImage(doc) ? documentPreviewUrl(doc.id) : null,
      scene: 'plaza' as const,
      accent: 0,
    })),
    permits: permitDocs.map((doc) => ({
      id: doc.id,
      title: doc.title,
      date: doc.documentDate,
    })),
    mediaStats: {
      ...emptyMediaStats(),
      photos: documents.filter(isImage).length,
      videos: documents.filter(isVideo).length,
      drone: documents.filter((doc) => doc.tags.toLowerCase().includes('drone')).length,
      renderings: 0,
      floorPlans: drawingDocs.length,
      documents: documents.length,
      lastUpdated: latest ? latest.slice(0, 10) : '',
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
