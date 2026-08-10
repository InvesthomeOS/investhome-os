/**
 * Website Builder ↔ Creative Studio draft_body_json mapping.
 * One serialize + one deserialize — no mapping scattered in UI components.
 *
 * Schema v2: heroImage / galleryImages as WbImageRef (asset_id primary).
 * Legacy v1 heroCoverOverride / galleryOverride URL strings are read on deserialize.
 */

import {
  DEFAULT_SECTIONS,
  DEFAULT_SPLIT_PRESET,
  normalizeWbSections,
  WB_STORAGE_KEY,
  type DevicePreview,
  type ProjectId,
  type PublishStatus,
  type SplitPanePreset,
  type WbPersistedState,
  type WbSection,
} from './website-builder-model';
import {
  normalizeLegacyImageFields,
  serializeImageRef,
  type WbImageRef,
} from './website-builder-media';

export const WB_DRAFT_SCHEMA_VERSION = 2 as const;
export const WB_MIGRATION_FLAG_KEY = 'ih-wb-draft-v3-migrated';
export const WB_EMERGENCY_SNAPSHOT_KEY = 'ih-wb-draft-v3-emergency';
/** Last explicitly selected construction project for Website Builder reload. */
export const WB_LAST_CONSTRUCTION_PROJECT_KEY = 'ih-wb-last-construction-project-id';

export type { WbImageRef };

/** Document content persisted to Creative Studio (excludes transient UI). */
export type WbDocumentDraft = {
  schemaVersion: typeof WB_DRAFT_SCHEMA_VERSION;
  linkedProjectId: string | null;
  sections: WbSection[];
  selectedSectionId: string;
  metaTitle: string;
  metaDesc: string;
  slug: string;
  publishStatus: PublishStatus;
  language: string;
  tone: string;
  brief: string;
  siteGoal: string;
  audience: string;
  mainMessage: string;
  heroTitle: string;
  heroBody: string;
  ctaPrimary: string;
  ctaSecondary: string;
  /** v2 primary image refs — asset_id preferred; never blob URLs. */
  heroImage: WbImageRef | null;
  galleryImages: WbImageRef[];
  /** Legacy demo project key — kept for localStorage migration only. */
  legacyProjectId?: ProjectId;
  /** Preview prefs from legacy LS; not required for API reopen. */
  device?: DevicePreview;
  zoom?: number;
  splitPreset?: SplitPanePreset;
  savedAt?: number;
};

export type WbEditorPersistInput = {
  linkedProjectId: string | null;
  sections: WbSection[];
  selectedSectionId: string;
  metaTitle: string;
  metaDesc: string;
  slug: string;
  publishStatus: PublishStatus;
  language: string;
  tone: string;
  brief: string;
  siteGoal: string;
  audience: string;
  mainMessage: string;
  heroTitle: string;
  heroBody: string;
  ctaPrimary: string;
  ctaSecondary: string;
  heroImage: WbImageRef | null;
  galleryImages: WbImageRef[];
  legacyProjectId?: ProjectId;
  device?: DevicePreview;
  zoom?: number;
  splitPreset?: SplitPanePreset;
};

export function serializeWebsiteBuilderDraft(
  input: WbEditorPersistInput,
): Record<string, unknown> {
  const heroSerialized = serializeImageRef(input.heroImage);
  const gallerySerialized = (input.galleryImages ?? [])
    .map((ref) => serializeImageRef(ref))
    .filter((ref): ref is Record<string, unknown> => ref != null);

  const draft: Record<string, unknown> = {
    schemaVersion: WB_DRAFT_SCHEMA_VERSION,
    linkedProjectId: input.linkedProjectId,
    sections: normalizeWbSections(input.sections),
    selectedSectionId: input.selectedSectionId || 's-hero',
    metaTitle: input.metaTitle ?? '',
    metaDesc: input.metaDesc ?? '',
    slug: input.slug ?? '',
    publishStatus: input.publishStatus ?? 'draft',
    language: input.language ?? 'tr',
    tone: input.tone ?? 'luxury',
    brief: input.brief ?? '',
    siteGoal: input.siteGoal ?? '',
    audience: input.audience ?? '',
    mainMessage: input.mainMessage ?? '',
    heroTitle: input.heroTitle ?? '',
    heroBody: input.heroBody ?? '',
    ctaPrimary: input.ctaPrimary ?? '',
    ctaSecondary: input.ctaSecondary ?? '',
    heroImage: heroSerialized,
    galleryImages: gallerySerialized,
    savedAt: Date.now(),
  };
  if (input.legacyProjectId) draft.legacyProjectId = input.legacyProjectId;
  if (input.device) draft.device = input.device;
  if (typeof input.zoom === 'number') draft.zoom = input.zoom;
  if (input.splitPreset) draft.splitPreset = input.splitPreset;
  return draft;
}

export function deserializeWebsiteBuilderDraft(
  raw: unknown,
): WbDocumentDraft | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;

  // Legacy localStorage shape (WbPersistedState)
  if (Array.isArray(body.sections) && typeof body.projectId === 'string') {
    const legacy = body as unknown as WbPersistedState;
    return {
      schemaVersion: WB_DRAFT_SCHEMA_VERSION,
      linkedProjectId: null,
      sections: normalizeWbSections(legacy.sections),
      selectedSectionId: legacy.selectedSectionId || 's-hero',
      metaTitle: legacy.metaTitle ?? '',
      metaDesc: legacy.metaDesc ?? '',
      slug: legacy.slug ?? '',
      publishStatus: legacy.publishStatus ?? 'draft',
      language: legacy.language ?? 'tr',
      tone: legacy.tone ?? 'luxury',
      brief: '',
      siteGoal: '',
      audience: '',
      mainMessage: '',
      heroTitle: '',
      heroBody: '',
      ctaPrimary: '',
      ctaSecondary: '',
      heroImage: null,
      galleryImages: [],
      legacyProjectId: legacy.projectId,
      device: legacy.device,
      zoom: legacy.zoom,
      splitPreset: legacy.splitPreset ?? DEFAULT_SPLIT_PRESET,
      savedAt: legacy.savedAt,
    };
  }

  if (!Array.isArray(body.sections)) return null;

  const { heroImage, galleryImages } = normalizeLegacyImageFields(body);

  return {
    schemaVersion: WB_DRAFT_SCHEMA_VERSION,
    linkedProjectId:
      typeof body.linkedProjectId === 'string' ? body.linkedProjectId : null,
    sections: normalizeWbSections(body.sections as WbSection[]),
    selectedSectionId:
      typeof body.selectedSectionId === 'string'
        ? body.selectedSectionId
        : 's-hero',
    metaTitle: typeof body.metaTitle === 'string' ? body.metaTitle : '',
    metaDesc: typeof body.metaDesc === 'string' ? body.metaDesc : '',
    slug: typeof body.slug === 'string' ? body.slug : '',
    publishStatus: (body.publishStatus as PublishStatus) || 'draft',
    language: typeof body.language === 'string' ? body.language : 'tr',
    tone: typeof body.tone === 'string' ? body.tone : 'luxury',
    brief: typeof body.brief === 'string' ? body.brief : '',
    siteGoal: typeof body.siteGoal === 'string' ? body.siteGoal : '',
    audience: typeof body.audience === 'string' ? body.audience : '',
    mainMessage: typeof body.mainMessage === 'string' ? body.mainMessage : '',
    heroTitle: typeof body.heroTitle === 'string' ? body.heroTitle : '',
    heroBody: typeof body.heroBody === 'string' ? body.heroBody : '',
    ctaPrimary: typeof body.ctaPrimary === 'string' ? body.ctaPrimary : '',
    ctaSecondary: typeof body.ctaSecondary === 'string' ? body.ctaSecondary : '',
    heroImage,
    galleryImages,
    legacyProjectId:
      typeof body.legacyProjectId === 'string'
        ? (body.legacyProjectId as ProjectId)
        : undefined,
    device: body.device as DevicePreview | undefined,
    zoom: typeof body.zoom === 'number' ? body.zoom : undefined,
    splitPreset: (body.splitPreset as SplitPanePreset) || undefined,
    savedAt: typeof body.savedAt === 'number' ? body.savedAt : undefined,
  };
}

/** True when API draft has no reusable editor content. */
export function isWebsiteBuilderDraftEmpty(raw: unknown): boolean {
  if (raw == null) return true;
  if (typeof raw !== 'object' || Array.isArray(raw)) return true;
  const keys = Object.keys(raw as object);
  if (keys.length === 0) return true;
  const draft = deserializeWebsiteBuilderDraft(raw);
  if (!draft) return true;
  const hasSections =
    Array.isArray(draft.sections) &&
    draft.sections.length > 0 &&
    draft.sections.some((s) => Boolean(s?.id && s?.key));
  const hasContent = Boolean(
    draft.heroTitle.trim() ||
      draft.heroBody.trim() ||
      draft.metaTitle.trim() ||
      draft.slug.trim() ||
      draft.brief.trim() ||
      draft.mainMessage.trim() ||
      draft.heroImage?.asset_id ||
      draft.heroImage?.url ||
      draft.galleryImages.length > 0,
  );
  // Empty shell with only default-looking sections and no content counts as empty
  // when sections equal defaults and no content fields are set.
  if (!hasContent) {
    if (!hasSections) return true;
    const onlyDefaults =
      draft.sections.length === DEFAULT_SECTIONS.length &&
      draft.sections.every(
        (s, i) => s.key === DEFAULT_SECTIONS[i]?.key && !s.customName,
      );
    if (onlyDefaults) return true;
  }
  return false;
}

export function loadLastConstructionProjectId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(WB_LAST_CONSTRUCTION_PROJECT_KEY);
    return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
  } catch {
    return null;
  }
}

export function saveLastConstructionProjectId(projectId: string): void {
  if (typeof window === 'undefined') return;
  const id = projectId.trim();
  if (!id) return;
  try {
    window.localStorage.setItem(WB_LAST_CONSTRUCTION_PROJECT_KEY, id);
  } catch {
    /* ignore quota */
  }
}

/** Prefer last explicit selection, then draft/emergency linkedProjectId. */
export function resolvePreferredConstructionProjectId(options: {
  projectIds: string[];
  lastSelectedId?: string | null;
  draftLinkedProjectId?: string | null;
}): string | null {
  const ids = new Set(options.projectIds.filter(Boolean));
  if (!ids.size) return null;
  const candidates = [options.lastSelectedId, options.draftLinkedProjectId];
  for (const candidate of candidates) {
    if (typeof candidate === 'string' && ids.has(candidate)) return candidate;
  }
  return null;
}

function peekLinkedProjectIdFromSnapshot(raw: string | null): string | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null;
    const linked = (parsed as Record<string, unknown>).linkedProjectId;
    return typeof linked === 'string' && linked.trim() ? linked.trim() : null;
  } catch {
    return null;
  }
}

/** Best-effort linkedProjectId from emergency snapshot or legacy draft. */
export function loadPersistedLinkedProjectIdHint(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const fromEmergency = peekLinkedProjectIdFromSnapshot(
      window.localStorage.getItem(WB_EMERGENCY_SNAPSHOT_KEY),
    );
    if (fromEmergency) return fromEmergency;
    const legacy = loadLegacyLocalStorageDraft();
    return legacy?.linkedProjectId ?? null;
  } catch {
    return null;
  }
}

export function loadLegacyLocalStorageDraft(): WbDocumentDraft | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(WB_STORAGE_KEY);
    if (!raw) return null;
    return deserializeWebsiteBuilderDraft(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function isLegacyMigrationDone(): boolean {
  if (typeof window === 'undefined') return true;
  try {
    return window.localStorage.getItem(WB_MIGRATION_FLAG_KEY) === '1';
  } catch {
    return true;
  }
}

export function markLegacyMigrationDone(): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(WB_MIGRATION_FLAG_KEY, '1');
  } catch {
    /* ignore */
  }
}

/** Emergency recovery snapshot only — never used to overwrite newer API data. */
export function saveEmergencySnapshot(draft: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      WB_EMERGENCY_SNAPSHOT_KEY,
      JSON.stringify({ ...draft, savedAt: Date.now() }),
    );
  } catch {
    /* ignore quota */
  }
}

/**
 * Migrate legacy LS → API only when API draft is empty and migration not done.
 * Returns draft to apply (API or migrated), and whether migration should be saved.
 */
export function resolveInitialDraft(options: {
  apiDraftBody: unknown;
  legacyDraft: WbDocumentDraft | null;
  migrationDone: boolean;
}): { draft: WbDocumentDraft | null; shouldMigrateToApi: boolean } {
  const apiEmpty = isWebsiteBuilderDraftEmpty(options.apiDraftBody);
  const apiDraft = deserializeWebsiteBuilderDraft(options.apiDraftBody);

  if (!apiEmpty && apiDraft) {
    return { draft: apiDraft, shouldMigrateToApi: false };
  }

  if (
    apiEmpty &&
    !options.migrationDone &&
    options.legacyDraft &&
    !isWebsiteBuilderDraftEmpty(options.legacyDraft)
  ) {
    return { draft: options.legacyDraft, shouldMigrateToApi: true };
  }

  return { draft: apiDraft, shouldMigrateToApi: false };
}
