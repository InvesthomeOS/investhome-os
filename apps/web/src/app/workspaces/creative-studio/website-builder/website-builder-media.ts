/**
 * Website Builder ↔ Creative Studio Media Library helpers.
 * Shared CsImageRef is primary; this module keeps WB-specific mapping + legacy migration.
 */

import type { CreativeStudioMediaAsset } from '@/lib/api/creative-studio';

import {
  CS_IMAGE_PLACEHOLDER,
  imageRefFromLegacyUrl,
  imageRefFromMediaAsset,
  isDemoAssetId,
  isEphemeralDisplayUrl,
  isMediaAssetUuid,
  isPersistableUrl,
  parseImageRef,
  resolveDisplayUrl,
  resolveGalleryDisplayUrls,
  sanitizeImageRef,
  serializeImageRef,
  type CsImageRef,
} from '../_components/cs-image-ref';
import { isActiveSelectableAsset } from '../_components/cs-media-selectability';

import type { AssetKind, AssetUsedIn, WbAsset } from './website-builder-model';

export type WbImageRef = CsImageRef;

export {
  CS_IMAGE_PLACEHOLDER as WB_IMAGE_PLACEHOLDER,
  imageRefFromLegacyUrl,
  imageRefFromMediaAsset,
  isDemoAssetId,
  isEphemeralDisplayUrl,
  isMediaAssetUuid,
  isPersistableUrl,
  parseImageRef,
  resolveDisplayUrl,
  resolveGalleryDisplayUrls,
  sanitizeImageRef,
  serializeImageRef,
};

export function imageRefFromWbAsset(asset: WbAsset, role?: string | null): WbImageRef | null {
  if (isMediaAssetUuid(asset.id)) {
    return {
      asset_id: asset.id,
      url: isPersistableUrl(asset.thumbUrl) ? asset.thumbUrl! : null,
      alt: asset.filename || null,
      focal: null,
      crop: null,
      role: role ?? null,
    };
  }
  // Demo / sample assets: URL only, never fake UUID
  if (asset.thumbUrl && isPersistableUrl(asset.thumbUrl)) {
    const url =
      asset.kind === 'images' || asset.kind === 'logos'
        ? asset.thumbUrl.replace('w=200&h=140', 'w=1600&h=900')
        : asset.thumbUrl;
    return imageRefFromLegacyUrl(url, role);
  }
  return null;
}

/**
 * Migrate v1 heroCoverOverride / galleryOverride URL strings into v2 WbImageRef fields.
 * Also accepts already-migrated heroImage / galleryImages.
 */
export function normalizeLegacyImageFields(body: Record<string, unknown>): {
  heroImage: WbImageRef | null;
  galleryImages: WbImageRef[];
} {
  const heroFromV2 = parseImageRef(body.heroImage);
  if (heroFromV2) {
    const galleryFromV2 = Array.isArray(body.galleryImages)
      ? body.galleryImages
          .map((item) => parseImageRef(item))
          .filter((item): item is WbImageRef => item != null)
      : [];
    return { heroImage: heroFromV2, galleryImages: galleryFromV2 };
  }

  const legacyHero =
    typeof body.heroCoverOverride === 'string' && isPersistableUrl(body.heroCoverOverride)
      ? imageRefFromLegacyUrl(body.heroCoverOverride, 'hero')
      : null;

  const legacyGallery = Array.isArray(body.galleryOverride)
    ? body.galleryOverride
        .filter((u): u is string => typeof u === 'string' && isPersistableUrl(u))
        .map((u) => imageRefFromLegacyUrl(u, 'gallery')!)
    : [];

  const galleryOnly = Array.isArray(body.galleryImages)
    ? body.galleryImages
        .map((item) => parseImageRef(item))
        .filter((item): item is WbImageRef => item != null)
    : [];

  return {
    heroImage: legacyHero,
    galleryImages: galleryOnly.length ? galleryOnly : legacyGallery,
  };
}

function kindFromContentType(contentType: string): AssetKind {
  const ct = contentType.toLowerCase();
  if (ct.startsWith('image/')) return 'images';
  if (ct.startsWith('video/')) return 'videos';
  if (ct === 'application/pdf') return 'pdf';
  if (ct.includes('dwg') || ct.includes('acad')) return 'dwg';
  if (ct.includes('presentation') || ct.includes('powerpoint')) return 'powerpoint';
  if (ct.includes('word') || ct.includes('msword') || ct.includes('document')) return 'word';
  return 'documents';
}

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function relativeUpdatedAt(iso: string): string {
  const then = Date.parse(iso);
  if (!Number.isFinite(then)) return '';
  const diffMs = Date.now() - then;
  if (diffMs < 60_000) return 'Just now';
  if (diffMs < 3_600_000) return `${Math.floor(diffMs / 60_000)}m ago`;
  if (diffMs < 86_400_000) return `${Math.floor(diffMs / 3_600_000)}h ago`;
  if (diffMs < 604_800_000) return `${Math.floor(diffMs / 86_400_000)}d ago`;
  return new Date(then).toLocaleDateString();
}

/** Map API media asset → picker card shape used by existing WB UI. */
export function mapMediaAssetToWbAsset(
  asset: CreativeStudioMediaAsset,
  displayThumbUrl?: string | null,
): WbAsset {
  const kind = kindFromContentType(asset.content_type || '');
  const ext = asset.filename.includes('.')
    ? asset.filename.split('.').pop()!.toUpperCase()
    : kind === 'images'
      ? 'IMG'
      : 'FILE';
  const resolution =
    asset.width && asset.height ? `${asset.width}×${asset.height}` : undefined;
  const metaParts = [
    resolution,
    formatBytes(asset.file_size),
    asset.archived_at ? 'Archived' : null,
    String(asset.sync_status || '').toLowerCase() === 'missing' ? 'Missing' : null,
  ].filter(Boolean);
  const folder =
    kind === 'images' || kind === 'logos' || kind === 'videos'
      ? 'renders'
      : kind === 'floorPlans' || kind === 'dwg'
        ? 'plans'
        : kind === 'brand'
          ? 'brand'
          : 'docs';
  const usedIn: AssetUsedIn[] | undefined = undefined;
  const thumb =
    displayThumbUrl ||
    (asset.thumbnail_url && isPersistableUrl(asset.thumbnail_url)
      ? asset.thumbnail_url
      : null) ||
    (kind === 'images' && isPersistableUrl(asset.url) ? asset.url : undefined);

  return {
    id: asset.id,
    kind,
    titleKey: asset.filename,
    filename: asset.filename,
    fileType: ext,
    meta: metaParts.join(' · ') || ext,
    resolution,
    folder,
    tags: Array.isArray(asset.tags) ? asset.tags : [],
    thumbUrl: thumb || undefined,
    usedIn,
    updatedAt: relativeUpdatedAt(asset.updated_at || asset.created_at),
  };
}

/** Whether a Media Library asset may be newly applied in Website Builder. */
export function canApplyMediaAsset(asset: CreativeStudioMediaAsset): boolean {
  return isActiveSelectableAsset(asset);
}
