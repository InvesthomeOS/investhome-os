/**
 * Social Media Builder construction-project selection + posts[] draft helpers.
 * Mirrors Presentation Builder last-project restore without changing other builders.
 */

import { isMediaAssetUuid } from '../_components/cs-image-ref';
import {
  createDefaultElements,
  captionFromElements,
  ensureUniqueElementIds,
  headlineFromElements,
  type SocialElement,
  type SocialStructuredMetric,
  type SocialTextAlign,
  type SocialTextRole,
} from './social-media-builder-elements';
import {
  createPostFromPreset,
  DEFAULT_POSTS,
  type ContentFormat,
  type FormatPresetKey,
  type PlatformKey,
  type PostStatus,
  type SocialPost,
} from './social-media-builder-model';

export const SMB_LAST_CONSTRUCTION_PROJECT_KEY = 'ih-smb-last-construction-project-id';
export const SMB_EMERGENCY_SNAPSHOT_KEY = 'ih-smb-draft-emergency';
export const SMB_DRAFT_SCHEMA_VERSION = 2 as const;

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

export function loadLastConstructionProjectId(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(SMB_LAST_CONSTRUCTION_PROJECT_KEY);
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
    window.localStorage.setItem(SMB_LAST_CONSTRUCTION_PROJECT_KEY, id);
  } catch {
    /* ignore quota */
  }
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

/** Best-effort linkedProjectId from emergency snapshot (reload before API resolve). */
export function loadPersistedLinkedProjectIdHint(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return peekLinkedProjectIdFromSnapshot(
      window.localStorage.getItem(SMB_EMERGENCY_SNAPSHOT_KEY),
    );
  } catch {
    return null;
  }
}

/** Emergency recovery snapshot — linkedProjectId hint + media refs + posts. */
export function saveEmergencySnapshot(draft: Record<string, unknown>): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(
      SMB_EMERGENCY_SNAPSHOT_KEY,
      JSON.stringify({ ...draft, savedAt: Date.now() }),
    );
  } catch {
    /* ignore quota */
  }
}

const FORMAT_PRESETS: FormatPresetKey[] = [
  'square',
  'portrait',
  'landscape',
  'story',
  'reelsCover',
  'carousel',
];

function asFormatPreset(raw: unknown): FormatPresetKey {
  return typeof raw === 'string' && (FORMAT_PRESETS as string[]).includes(raw)
    ? (raw as FormatPresetKey)
    : 'square';
}

function asPlatform(raw: unknown): PlatformKey {
  if (raw === 'facebook' || raw === 'linkedin' || raw === 'x' || raw === 'instagram') {
    return raw;
  }
  return 'instagram';
}

function asPostStatus(raw: unknown): PostStatus {
  if (raw === 'ready' || raw === 'draft' || raw === 'scheduled' || raw === 'review') {
    return raw;
  }
  return 'draft';
}

function asContentFormat(raw: unknown, preset: FormatPresetKey): ContentFormat {
  if (
    raw === 'feed' ||
    raw === 'story' ||
    raw === 'reel' ||
    raw === 'carousel' ||
    raw === 'post' ||
    raw === 'short' ||
    raw === 'video' ||
    raw === 'thread'
  ) {
    return raw;
  }
  if (preset === 'story') return 'story';
  if (preset === 'reelsCover') return 'reel';
  if (preset === 'carousel') return 'carousel';
  return 'feed';
}

function clampNum(raw: unknown, fallback: number): number {
  const n = typeof raw === 'number' ? raw : Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

function parseElement(raw: unknown): SocialElement | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const type = body.type;
  const id = typeof body.id === 'string' && body.id.trim() ? body.id.trim() : null;
  if (!id) return null;
  const base = {
    id,
    x: clampNum(body.x, 0),
    y: clampNum(body.y, 0),
    width: Math.max(1, clampNum(body.width, 100)),
    height: Math.max(1, clampNum(body.height, 40)),
    zIndex: Math.round(clampNum(body.zIndex, 1)),
  };

  if (type === 'TEXT') {
    const alignRaw = body.align;
    const align: SocialTextAlign =
      alignRaw === 'left' || alignRaw === 'right' || alignRaw === 'center'
        ? alignRaw
        : 'center';
    const roleRaw = body.role;
    const role: SocialTextRole =
      roleRaw === 'headline' || roleRaw === 'body' || roleRaw === 'custom' || roleRaw === 'eyebrow'
        ? roleRaw
        : 'custom';
    const fontWeight = body.fontWeight === 'bold' ? 'bold' : 'normal';
    return {
      ...base,
      type: 'TEXT',
      content: typeof body.content === 'string' ? body.content : '',
      fontSize: Math.max(8, clampNum(body.fontSize, 24)),
      fontWeight,
      align,
      color: typeof body.color === 'string' && body.color.trim() ? body.color : '#ffffff',
      role,
    };
  }

  if (type === 'IMAGE') {
    const assetRaw =
      typeof body.assetId === 'string'
        ? body.assetId
        : typeof body.asset_id === 'string'
          ? body.asset_id
          : null;
    return {
      ...base,
      type: 'IMAGE',
      assetId: assetRaw && isMediaAssetUuid(assetRaw) ? assetRaw.trim() : null,
    };
  }

  if (type === 'BUTTON' || type === 'CTA') {
    return {
      ...base,
      type: 'BUTTON',
      label: typeof body.label === 'string' ? body.label : 'Call to action',
      backgroundColor:
        typeof body.backgroundColor === 'string' && body.backgroundColor.trim()
          ? body.backgroundColor
          : '#ffffff',
      textColor:
        typeof body.textColor === 'string' && body.textColor.trim()
          ? body.textColor
          : '#111827',
    };
  }

  if (type === 'METRIC_GROUP') {
    const layoutRaw = body.layout;
    const layout =
      layoutRaw === 'stacked' || layoutRaw === 'cards' || layoutRaw === 'horizontal'
        ? layoutRaw
        : 'horizontal';
    const metricsRaw = Array.isArray(body.metrics) ? body.metrics : [];
    const metrics = metricsRaw
      .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
      .slice(0, 3)
      .map((row, index) => {
        const emphasisRaw = row.emphasis;
        const emphasis =
          emphasisRaw === 'primary' || emphasisRaw === 'secondary' || emphasisRaw === 'tertiary'
            ? emphasisRaw
            : 'secondary';
        const typeRaw = typeof row.type === 'string' ? row.type : 'generic_numeric';
        const rawValue = row.raw_value;
        return {
          id: typeof row.id === 'string' && row.id.trim() ? row.id : `metric-${index + 1}`,
          type: typeRaw as SocialStructuredMetric['type'],
          raw_value:
            typeof rawValue === 'number' || typeof rawValue === 'string' ? rawValue : '',
          display_value: typeof row.display_value === 'string' ? row.display_value : '',
          label: typeof row.label === 'string' ? row.label : '',
          unit: typeof row.unit === 'string' ? row.unit : '',
          locale: typeof row.locale === 'string' ? row.locale : 'en',
          emphasis,
          source_token: typeof row.source_token === 'string' ? row.source_token : '',
        };
      });
    if (!metrics.length) return null;
    return {
      ...base,
      type: 'METRIC_GROUP',
      layout,
      metrics,
      color: typeof body.color === 'string' && body.color.trim() ? body.color : '#ffffff',
    };
  }

  return null;
}

function serializeElement(el: SocialElement): Record<string, unknown> {
  const base = {
    id: el.id,
    type: el.type,
    x: el.x,
    y: el.y,
    width: el.width,
    height: el.height,
    zIndex: el.zIndex,
  };
  if (el.type === 'TEXT') {
    return {
      ...base,
      content: el.content,
      fontSize: el.fontSize,
      fontWeight: el.fontWeight,
      align: el.align,
      color: el.color,
      role: el.role,
    };
  }
  if (el.type === 'IMAGE') {
    return {
      ...base,
      assetId: el.assetId && isMediaAssetUuid(el.assetId) ? el.assetId : null,
    };
  }
  if (el.type === 'METRIC_GROUP') {
    return {
      ...base,
      layout: el.layout,
      metrics: el.metrics,
      color: el.color,
    };
  }
  return {
    ...base,
    label: el.label,
    backgroundColor: el.backgroundColor,
    textColor: el.textColor,
  };
}

export function serializeSocialPost(post: SocialPost): Record<string, unknown> {
  return {
    id: post.id,
    platform: post.platform,
    format: post.format,
    formatPreset: post.formatPreset,
    width: post.width,
    height: post.height,
    status: post.status,
    name: post.name,
    description: post.description,
    headline: headlineFromElements(post.elements) || post.headline,
    caption: captionFromElements(post.elements) || post.caption,
    coverAssetId:
      post.coverAssetId && isMediaAssetUuid(post.coverAssetId) ? post.coverAssetId : null,
    linked_project_id:
      post.linkedProjectId && post.linkedProjectId.trim()
        ? post.linkedProjectId.trim()
        : null,
    elements: post.elements.map(serializeElement),
    ...(post.generationMeta && typeof post.generationMeta === 'object'
      ? { generationMeta: post.generationMeta }
      : {}),
    ...(post.compositionStrategy ? { compositionStrategy: post.compositionStrategy } : {}),
    ...(post.overlayStrategy ? { overlayStrategy: post.overlayStrategy } : {}),
    ...(post.textAlign ? { textAlign: post.textAlign } : {}),
    ...(post.safeTextZone ? { safeTextZone: post.safeTextZone } : {}),
  };
}

export function parseSocialPost(
  raw: unknown,
  fallbackLinkedProjectId: string | null = null,
): SocialPost | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const id = typeof body.id === 'string' && body.id.trim() ? body.id.trim() : null;
  if (!id) return null;
  const formatPreset = asFormatPreset(body.formatPreset ?? body.format_preset);
  const width = Math.max(1, clampNum(body.width, 1080));
  const height = Math.max(1, clampNum(body.height, 1080));
  const headline = typeof body.headline === 'string' ? body.headline : '';
  const caption = typeof body.caption === 'string' ? body.caption : '';
  const parsedElements = Array.isArray(body.elements)
    ? body.elements.map(parseElement).filter((e): e is SocialElement => e != null)
    : [];
  const elements = ensureUniqueElementIds(
    parsedElements.length > 0
      ? parsedElements
      : createDefaultElements(width, height, { headline, caption }),
  );

  const coverRaw =
    typeof body.coverAssetId === 'string'
      ? body.coverAssetId
      : typeof body.cover_asset_id === 'string'
        ? body.cover_asset_id
        : null;
  const linkedRaw =
    typeof body.linked_project_id === 'string'
      ? body.linked_project_id
      : typeof body.linkedProjectId === 'string'
        ? body.linkedProjectId
        : fallbackLinkedProjectId;

  return {
    id,
    platform: asPlatform(body.platform),
    format: asContentFormat(body.format, formatPreset),
    formatPreset,
    width,
    height,
    status: asPostStatus(body.status),
    thumbUrl: '',
    name: typeof body.name === 'string' ? body.name : 'Social post',
    headline: headlineFromElements(elements) || headline,
    description: typeof body.description === 'string' ? body.description : '',
    caption: captionFromElements(elements) || caption,
    coverAssetId: coverRaw && isMediaAssetUuid(coverRaw) ? coverRaw.trim() : null,
    linkedProjectId:
      typeof linkedRaw === 'string' && linkedRaw.trim() ? linkedRaw.trim() : null,
    elements,
    generationMeta:
      body.generationMeta && typeof body.generationMeta === 'object' && !Array.isArray(body.generationMeta)
        ? (body.generationMeta as Record<string, unknown>)
        : null,
    compositionStrategy: typeof body.compositionStrategy === 'string' ? body.compositionStrategy : null,
    overlayStrategy: typeof body.overlayStrategy === 'string' ? body.overlayStrategy : null,
    textAlign:
      body.textAlign === 'left' || body.textAlign === 'center' || body.textAlign === 'right'
        ? body.textAlign
        : null,
    safeTextZone: typeof body.safeTextZone === 'string' ? body.safeTextZone : null,
  };
}

export function serializeSocialPosts(posts: SocialPost[]): Record<string, unknown>[] {
  return posts.map(serializeSocialPost);
}

export function parseSocialPosts(
  raw: unknown,
  fallbackLinkedProjectId: string | null = null,
): SocialPost[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => parseSocialPost(item, fallbackLinkedProjectId))
    .filter((p): p is SocialPost => p != null);
}

/**
 * Cover-image-only drafts → one post with default TEXT/BUTTON elements + cover Asset ID.
 * Existing posts[] drafts are returned as-is (with element parse/migration).
 */
export function hydrateSocialPostsFromDraft(input: {
  posts?: unknown;
  coverAssetId?: string | null;
  linkedProjectId?: string | null;
  selectedPostId?: string | null;
  seedDefaults?: boolean;
}): { posts: SocialPost[]; selectedPostId: string } {
  const linked = input.linkedProjectId ?? null;
  const parsed = parseSocialPosts(input.posts, linked);
  if (parsed.length) {
    const withCover = parsed.map((p, i) => {
      const cover =
        p.coverAssetId ||
        (i === 0 && input.coverAssetId && isMediaAssetUuid(input.coverAssetId)
          ? input.coverAssetId
          : null);
      return {
        ...p,
        coverAssetId: cover,
        linkedProjectId: p.linkedProjectId || linked,
      };
    });
    const selected =
      (input.selectedPostId && withCover.some((p) => p.id === input.selectedPostId)
        ? input.selectedPostId
        : withCover[0]!.id);
    return { posts: withCover, selectedPostId: selected };
  }

  if (input.seedDefaults === false && !input.coverAssetId) {
    const fresh = createPostFromPreset('square', 1, {
      coverAssetId: null,
      linkedProjectId: linked,
    });
    return { posts: [fresh], selectedPostId: fresh.id };
  }

  const base = DEFAULT_POSTS.map((p, i) => ({
    ...p,
    linkedProjectId: linked,
    coverAssetId:
      i === 0 && input.coverAssetId && isMediaAssetUuid(input.coverAssetId)
        ? input.coverAssetId
        : null,
    elements:
      p.elements?.length > 0
        ? p.elements
        : createDefaultElements(p.width, p.height, {
            headline: p.headline,
            caption: p.caption,
          }),
  }));
  return { posts: base, selectedPostId: base[0]!.id };
}

export function collectPostAssetIds(posts: SocialPost[]): string[] {
  const ids: string[] = [];
  const seen = new Set<string>();
  const push = (id: string | null | undefined) => {
    if (!id || !isMediaAssetUuid(id) || seen.has(id)) return;
    seen.add(id);
    ids.push(id);
  };
  for (const post of posts) {
    push(post.coverAssetId);
    for (const el of post.elements) {
      if (el.type === 'IMAGE') push(el.assetId);
    }
  }
  return ids;
}
