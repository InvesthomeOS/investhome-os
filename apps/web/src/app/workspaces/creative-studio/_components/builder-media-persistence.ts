/**
 * Shared Creative Studio builder draft ↔ draft_body_json mapping for media Asset IDs.
 * Used by Landing, Blog, Email, Proposal, Presentation, Social builders.
 *
 * Persists CsImageRef (asset_id primary). Never Drive paths, blob URLs, or filenames as identity.
 * Legacy URL-only drafts remain readable; replacing with ML asset saves Asset ID format.
 */

import {
  imageRefFromLegacyUrl,
  parseImageRef,
  serializeImageRef,
  type CsImageRef,
} from './cs-image-ref';
import type { CreativeStudioDocumentType } from '@/lib/api/creative-studio';

export const BUILDER_MEDIA_DRAFT_SCHEMA_VERSION = 1 as const;

export type BuilderMediaDocumentType =
  | 'landing'
  | 'blog'
  | 'email'
  | 'proposal'
  | 'presentation'
  | 'social';

export const BUILDER_MEDIA_DOCUMENT_TYPES: BuilderMediaDocumentType[] = [
  'landing',
  'blog',
  'email',
  'proposal',
  'presentation',
  'social',
];

export const BUILDER_KIND_LABELS: Record<BuilderMediaDocumentType, string> = {
  landing: 'Landing',
  blog: 'Blog',
  email: 'Email',
  proposal: 'Proposal',
  presentation: 'Presentation',
  social: 'Social',
};

export type BuilderMediaDraft = {
  schemaVersion: typeof BUILDER_MEDIA_DRAFT_SCHEMA_VERSION;
  documentType: BuilderMediaDocumentType;
  linkedProjectId: string | null;
  /** Cover / hero / featured image — Asset ID preferred. */
  coverImage: CsImageRef | null;
  /** Optional gallery (Landing); empty for cover-only builders. */
  galleryImages: CsImageRef[];
  savedAt?: number;
};

export type BuilderMediaPersistInput = {
  documentType: BuilderMediaDocumentType;
  linkedProjectId: string | null;
  coverImage: CsImageRef | null;
  galleryImages?: CsImageRef[];
};

export function isBuilderMediaDocumentType(
  value: string,
): value is BuilderMediaDocumentType {
  return (BUILDER_MEDIA_DOCUMENT_TYPES as string[]).includes(value);
}

export function serializeBuilderMediaDraft(
  input: BuilderMediaPersistInput,
): Record<string, unknown> {
  const coverSerialized = serializeImageRef(input.coverImage);
  const gallerySerialized = (input.galleryImages ?? [])
    .map((ref) => serializeImageRef(ref))
    .filter((ref): ref is Record<string, unknown> => ref != null);

  return {
    schemaVersion: BUILDER_MEDIA_DRAFT_SCHEMA_VERSION,
    documentType: input.documentType,
    linkedProjectId: input.linkedProjectId,
    coverImage: coverSerialized,
    galleryImages: gallerySerialized,
    savedAt: Date.now(),
  };
}

/**
 * Normalize cover from coverImage, heroImage, or legacy URL string fields.
 */
export function normalizeBuilderCoverFields(body: Record<string, unknown>): {
  coverImage: CsImageRef | null;
  galleryImages: CsImageRef[];
} {
  const cover =
    parseImageRef(body.coverImage) ||
    parseImageRef(body.heroImage) ||
    (typeof body.coverUrl === 'string'
      ? imageRefFromLegacyUrl(body.coverUrl, 'cover')
      : null) ||
    (typeof body.heroCoverOverride === 'string'
      ? imageRefFromLegacyUrl(body.heroCoverOverride, 'cover')
      : null);

  const galleryFromRefs = Array.isArray(body.galleryImages)
    ? body.galleryImages
        .map((item) => parseImageRef(item))
        .filter((item): item is CsImageRef => item != null)
    : [];

  const galleryFromLegacy = Array.isArray(body.galleryOverride)
    ? body.galleryOverride
        .filter((u): u is string => typeof u === 'string')
        .map((u) => imageRefFromLegacyUrl(u, 'gallery'))
        .filter((item): item is CsImageRef => item != null)
    : [];

  const galleryFromUrls = Array.isArray(body.galleryUrls)
    ? body.galleryUrls
        .filter((u): u is string => typeof u === 'string')
        .map((u) => imageRefFromLegacyUrl(u, 'gallery'))
        .filter((item): item is CsImageRef => item != null)
    : [];

  return {
    coverImage: cover,
    galleryImages: galleryFromRefs.length
      ? galleryFromRefs
      : galleryFromLegacy.length
        ? galleryFromLegacy
        : galleryFromUrls,
  };
}

export function deserializeBuilderMediaDraft(
  raw: unknown,
  fallbackType: BuilderMediaDocumentType,
): BuilderMediaDraft | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const { coverImage, galleryImages } = normalizeBuilderCoverFields(body);

  const typeRaw =
    typeof body.documentType === 'string' ? body.documentType : fallbackType;
  const documentType = isBuilderMediaDocumentType(typeRaw)
    ? typeRaw
    : fallbackType;

  // Empty object → null draft (caller seeds from template)
  const keys = Object.keys(body);
  if (keys.length === 0) return null;
  if (!coverImage && galleryImages.length === 0 && keys.length <= 2) {
    // schemaVersion / documentType only
    const onlyMeta = keys.every((k) =>
      ['schemaVersion', 'documentType', 'linkedProjectId', 'savedAt'].includes(k),
    );
    if (onlyMeta) return null;
  }

  return {
    schemaVersion: BUILDER_MEDIA_DRAFT_SCHEMA_VERSION,
    documentType,
    linkedProjectId:
      typeof body.linkedProjectId === 'string' ? body.linkedProjectId : null,
    coverImage,
    galleryImages,
    savedAt: typeof body.savedAt === 'number' ? body.savedAt : undefined,
  };
}

/** True when draft has no media refs worth applying. */
export function isBuilderMediaDraftEmpty(raw: unknown): boolean {
  if (raw == null) return true;
  if (typeof raw !== 'object' || Array.isArray(raw)) return true;
  const keys = Object.keys(raw as object);
  if (keys.length === 0) return true;
  const { coverImage, galleryImages } = normalizeBuilderCoverFields(
    raw as Record<string, unknown>,
  );
  return !coverImage && galleryImages.length === 0;
}

/** Assert serialized draft never contains Drive paths or ephemeral URLs. */
export function assertSafeBuilderMediaDraft(
  draft: Record<string, unknown>,
): { ok: true } | { ok: false; reason: string } {
  const blob = JSON.stringify(draft);
  if (/blob:/i.test(blob) || /filesystem:/i.test(blob) || /object:/i.test(blob)) {
    return { ok: false, reason: 'ephemeral url' };
  }
  if (/drive\.google\.com/i.test(blob) || /\/file\/d\//i.test(blob)) {
    return { ok: false, reason: 'drive path' };
  }
  const cover = draft.coverImage as Record<string, unknown> | null | undefined;
  if (cover && typeof cover === 'object') {
    if ('drive_file_id' in cover || 'driveFileId' in cover || 'path' in cover) {
      return { ok: false, reason: 'drive identity field' };
    }
  }
  return { ok: true };
}

export function asCreativeStudioDocumentType(
  type: BuilderMediaDocumentType,
): CreativeStudioDocumentType {
  return type;
}
