/**
 * Shared Creative Studio image reference helpers.
 * Asset ID is primary; URLs are legacy or optional stable API paths (never blob:/object:).
 */

import {
  getCreativeStudioMediaContentUrl,
  type CreativeStudioMediaAsset,
} from '@/lib/api/creative-studio';

export type CsImageRef = {
  asset_id: string | null;
  /** Legacy URL or optional stable API content path — never blob: / object: */
  url?: string | null;
  alt?: string | null;
  focal?: string | null;
  crop?: string | null;
  role?: string | null;
};

/** @deprecated Prefer CsImageRef — kept as alias for Website Builder callers. */
export type WbImageRef = CsImageRef;

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

export function parseImageRef(raw: unknown): CsImageRef | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const assetRaw =
    typeof body.asset_id === 'string'
      ? body.asset_id
      : typeof body.assetId === 'string'
        ? body.assetId
        : null;
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

export function sanitizeImageRef(ref: CsImageRef | null | undefined): CsImageRef | null {
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
  ref: CsImageRef | null | undefined,
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
): CsImageRef | null {
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
): CsImageRef {
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

/**
 * Display URL priority for a single image slot:
 * 1. resolved asset blob/content (caller-supplied)
 * 2. legacy / cached persistable url on the ref
 * 3. template/default url
 * 4. null → caller uses placeholder
 */
export function resolveDisplayUrl(options: {
  ref: CsImageRef | null | undefined;
  resolvedAssetUrl?: string | null;
  templateUrl?: string | null;
  placeholderUrl?: string | null;
}): string | null {
  const { ref, resolvedAssetUrl, templateUrl, placeholderUrl } = options;
  if (resolvedAssetUrl) return resolvedAssetUrl;
  if (ref?.url && isPersistableUrl(ref.url)) return ref.url;
  if (templateUrl) return templateUrl;
  if (placeholderUrl) return placeholderUrl;
  return null;
}

export function resolveGalleryDisplayUrls(options: {
  refs: CsImageRef[];
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
          }) ??
          placeholderUrl ??
          ''
        );
      })
      .filter(Boolean);
  }
  if (templateUrls.length) return [...templateUrls];
  if (placeholderUrl) return [placeholderUrl];
  return [];
}

export const CS_IMAGE_PLACEHOLDER =
  'data:image/svg+xml,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
      <rect fill="#e8eef3" width="1600" height="900"/>
      <text x="50%" y="50%" fill="#6b7c8f" font-family="system-ui,sans-serif" font-size="28" text-anchor="middle" dy=".3em">Image unavailable</text>
    </svg>`,
  );
