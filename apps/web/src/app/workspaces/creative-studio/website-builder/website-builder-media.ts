/**
 * Website Builder ↔ Creative Studio Media Library helpers.
 * Asset ID is primary; URLs are legacy or optional stable API paths (never blob:/object:).
 */

import {
  getCreativeStudioMediaContentUrl,
  type CreativeStudioMediaAsset,
} from '@/lib/api/creative-studio';

import type { AssetKind, AssetUsedIn, WbAsset } from './website-builder-model';

export type WbImageRef = {
  asset_id: string | null;
  /** Legacy URL or optional stable API content path — never blob: / object: */
  url?: string | null;
  alt?: string | null;
  focal?: string | null;
  crop?: string | null;
  role?: string | null;
};

/** Demo picker ids like `a1` must never be treated as Media Library UUIDs. */
const DEMO_ASSET_ID_RE = /^a\d+$/i;
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function isDemoAssetId(id: string | null | undefined): boolean {
  if (!id) return false;
  return DEMO_ASSET_ID_RE.test(id.trim());
}

export function isMediaAssetUuid(id: string | null | undefined): boolean {
  if (!id) return false;
  const trimmed = id.trim();
  if (isDemoAssetId(trimmed)) return false;
  return UUID_RE.test(trimmed);
}

export function isEphemeralDisplayUrl(url: string | null | undefined): boolean {
  if (!url) return false;
  const lower = url.trim().toLowerCase();
  return (
    lower.startsWith('blob:') ||
    lower.startsWith('object:') ||
    lower.startsWith('filesystem:')
  );
}

export function isPersistableUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
  if (!trimmed) return false;
  if (isEphemeralDisplayUrl(trimmed)) return false;
  return true;
}

export function parseImageRef(raw: unknown): WbImageRef | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const assetRaw =
    typeof body.asset_id === 'string'
      ? body.asset_id
      : typeof body.assetId === 'string'
        ? body.assetId
        : null;
  // Demo ids like `a1` and non-UUIDs are never stored as asset_id
  const safeAssetId =
    assetRaw && isMediaAssetUuid(assetRaw) ? assetRaw.trim() : null;

  const urlRaw =
    typeof body.url === 'string'
      ? body.url
      : typeof body.src === 'string'
        ? body.src
        : null;
  const url = isPersistableUrl(urlRaw) ? urlRaw!.trim() : null;

  if (!safeAssetId && !url) return null;

  return {
    asset_id: safeAssetId,
    url,
    alt: typeof body.alt === 'string' ? body.alt : null,
    focal: typeof body.focal === 'string' ? body.focal : null,
    crop: typeof body.crop === 'string' ? body.crop : null,
    role: typeof body.role === 'string' ? body.role : null,
  };
}

export function sanitizeImageRef(ref: WbImageRef | null | undefined): WbImageRef | null {
  if (!ref) return null;
  const asset_id =
    ref.asset_id && isMediaAssetUuid(ref.asset_id) ? ref.asset_id : null;
  const url = isPersistableUrl(ref.url) ? ref.url!.trim() : null;
  if (!asset_id && !url) return null;
  return {
    asset_id,
    url,
    alt: ref.alt ?? null,
    focal: ref.focal ?? null,
    crop: ref.crop ?? null,
    role: ref.role ?? null,
  };
}

export function serializeImageRef(
  ref: WbImageRef | null | undefined,
): Record<string, unknown> | null {
  const clean = sanitizeImageRef(ref);
  if (!clean) return null;
  const out: Record<string, unknown> = {
    asset_id: clean.asset_id,
  };
  if (clean.url) out.url = clean.url;
  if (clean.alt) out.alt = clean.alt;
  if (clean.focal) out.focal = clean.focal;
  if (clean.crop) out.crop = clean.crop;
  if (clean.role) out.role = clean.role;
  return out;
}

export function imageRefFromLegacyUrl(
  url: string,
  role?: string | null,
): WbImageRef | null {
  if (!isPersistableUrl(url)) return null;
  return {
    asset_id: null,
    url: url.trim(),
    alt: null,
    focal: null,
    crop: null,
    role: role ?? null,
  };
}

export function imageRefFromMediaAsset(
  asset: Pick<CreativeStudioMediaAsset, 'id' | 'filename' | 'url'>,
  role?: string | null,
): WbImageRef {
  const stableUrl =
    typeof asset.url === 'string' && isPersistableUrl(asset.url)
      ? asset.url
      : isMediaAssetUuid(asset.id)
        ? getCreativeStudioMediaContentUrl(asset.id)
        : null;
  return {
    asset_id: isMediaAssetUuid(asset.id) ? asset.id : null,
    url: stableUrl,
    alt: asset.filename || null,
    focal: null,
    crop: null,
    role: role ?? null,
  };
}

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

  // galleryImages without heroImage
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

/**
 * Display URL priority for a single image slot:
 * 1. resolved asset blob/content (caller-supplied)
 * 2. legacy / cached persistable url on the ref
 * 3. template/default url
 * 4. null → caller uses placeholder
 */
export function resolveDisplayUrl(options: {
  ref: WbImageRef | null | undefined;
  resolvedAssetUrl?: string | null;
  templateUrl?: string | null;
  placeholderUrl?: string | null;
}): string | null {
  const { ref, resolvedAssetUrl, templateUrl, placeholderUrl } = options;
  // Resolved blob/content URLs are valid for display (never persist them).
  if (resolvedAssetUrl) return resolvedAssetUrl;

  if (ref?.url && isPersistableUrl(ref.url)) return ref.url;

  if (templateUrl) return templateUrl;
  if (placeholderUrl) return placeholderUrl;
  return null;
}

export function resolveGalleryDisplayUrls(options: {
  refs: WbImageRef[];
  resolvedByAssetId?: Record<string, string>;
  templateUrls?: string[];
  placeholderUrl?: string | null;
}): string[] {
  const { refs, resolvedByAssetId = {}, templateUrls = [], placeholderUrl } = options;
  if (refs.length) {
    return refs
      .map((ref, index) => {
        const resolved =
          ref.asset_id && resolvedByAssetId[ref.asset_id]
            ? resolvedByAssetId[ref.asset_id]
            : null;
        return (
          resolveDisplayUrl({
            ref,
            resolvedAssetUrl: resolved,
            templateUrl: templateUrls[index] ?? templateUrls[0] ?? null,
            placeholderUrl,
          }) ?? placeholderUrl ?? ''
        );
      })
      .filter(Boolean);
  }
  if (templateUrls.length) return [...templateUrls];
  if (placeholderUrl) return [placeholderUrl];
  return [];
}

export const WB_IMAGE_PLACEHOLDER =
  'data:image/svg+xml,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
      <rect fill="#e8eef3" width="1600" height="900"/>
      <text x="50%" y="50%" fill="#6b7c8f" font-family="system-ui,sans-serif" font-size="28" text-anchor="middle" dy=".3em">Image unavailable</text>
    </svg>`,
  );
