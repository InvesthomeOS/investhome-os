/**
 * Social Media Builder construction-project selection + posts[] draft helpers.
 * Mirrors Presentation Builder last-project restore without changing other builders.
 */

import { isMediaAssetUuid } from '../_components/cs-image-ref';
import {
  clampOpacity,
  createDefaultElements,
  captionFromElements,
  ensureUniqueElementIds,
  headlineFromElements,
  parseSocialFontFamily,
  parseSocialFontWeight,
  parseSocialObjectFit,
  type SocialElement,
  type SocialImageElement,
  type SocialStructuredMetric,
  type SocialTextAlign,
  type SocialTextRole,
} from './social-media-builder-elements';
import {
  createPostFromPreset,
  DEFAULT_POSTS,
  PLACEHOLDER_HEADLINE,
  type ContentFormat,
  type FormatPresetKey,
  type PlatformKey,
  type PostStatus,
  type SocialPost,
  type SocialPostGenerationLifecycle,
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

function asOptionalId(raw: unknown): string | null {
  return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
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
      roleRaw === 'headline' ||
      roleRaw === 'body' ||
      roleRaw === 'custom' ||
      roleRaw === 'eyebrow' ||
      roleRaw === 'brand'
        ? roleRaw
        : 'custom';
    const fontFamily = parseSocialFontFamily(body.fontFamily);
    const lineHeight =
      typeof body.lineHeight === 'number' && Number.isFinite(body.lineHeight)
        ? Math.max(0.8, Math.min(3, body.lineHeight))
        : undefined;
    const letterSpacing =
      typeof body.letterSpacing === 'number' && Number.isFinite(body.letterSpacing)
        ? Math.max(-5, Math.min(40, body.letterSpacing))
        : undefined;
    const opacity =
      body.opacity === undefined || body.opacity === null
        ? undefined
        : clampOpacity(body.opacity, 1);
    return {
      ...base,
      type: 'TEXT',
      content: typeof body.content === 'string' ? body.content : '',
      fontSize: Math.max(8, clampNum(body.fontSize, 24)),
      fontWeight: parseSocialFontWeight(body.fontWeight),
      align,
      color: typeof body.color === 'string' && body.color.trim() ? body.color : '#ffffff',
      role,
      ...(fontFamily ? { fontFamily } : {}),
      ...(lineHeight !== undefined ? { lineHeight } : {}),
      ...(letterSpacing !== undefined ? { letterSpacing } : {}),
      ...(opacity !== undefined ? { opacity } : {}),
    };
  }

  if (type === 'IMAGE') {
    const assetRaw =
      typeof body.assetId === 'string'
        ? body.assetId
        : typeof body.asset_id === 'string'
          ? body.asset_id
          : null;
    const roleRaw = body.role;
    const role =
      roleRaw === 'background' || roleRaw === 'cover' || roleRaw === 'logo' || roleRaw === 'image'
        ? roleRaw
        : undefined;
    const objectFit = parseSocialObjectFit(body.objectFit);
    const opacity =
      body.opacity === undefined || body.opacity === null
        ? undefined
        : clampOpacity(body.opacity, 1);
    return {
      ...base,
      type: 'IMAGE',
      assetId: assetRaw && isMediaAssetUuid(assetRaw) ? assetRaw.trim() : null,
      ...(role ? { role } : {}),
      ...(body.crop && typeof body.crop === 'object' && !Array.isArray(body.crop)
        ? { crop: body.crop as SocialImageElement['crop'] }
        : {}),
      ...(typeof body.objectPosition === 'string' ? { objectPosition: body.objectPosition } : {}),
      ...(objectFit ? { objectFit } : {}),
      ...(typeof body.lockAspectRatio === 'boolean' ? { lockAspectRatio: body.lockAspectRatio } : {}),
      ...(opacity !== undefined ? { opacity } : {}),
    };
  }

  if (type === 'BUTTON' || type === 'CTA') {
    const fontFamily = parseSocialFontFamily(body.fontFamily);
    const alignRaw = body.align;
    const align: SocialTextAlign | undefined =
      alignRaw === 'left' || alignRaw === 'right' || alignRaw === 'center' ? alignRaw : undefined;
    const opacity =
      body.opacity === undefined || body.opacity === null
        ? undefined
        : clampOpacity(body.opacity, 1);
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
      ctaStyle: typeof body.ctaStyle === 'string' ? body.ctaStyle : null,
      ...(typeof body.fontSize === 'number' && Number.isFinite(body.fontSize)
        ? { fontSize: Math.max(8, Math.round(body.fontSize)) }
        : {}),
      ...(body.fontWeight !== undefined
        ? { fontWeight: parseSocialFontWeight(body.fontWeight) }
        : {}),
      ...(fontFamily ? { fontFamily } : {}),
      ...(align ? { align } : {}),
      ...(typeof body.borderRadius === 'number' && Number.isFinite(body.borderRadius)
        ? { borderRadius: Math.max(0, Math.round(body.borderRadius)) }
        : {}),
      ...(typeof body.padding === 'number' && Number.isFinite(body.padding)
        ? { padding: Math.max(0, Math.round(body.padding)) }
        : {}),
      ...(opacity !== undefined ? { opacity } : {}),
    };
  }

  if (type === 'SHAPE') {
    const kindRaw = body.shapeKind ?? body.shape_kind;
    const shapeKind =
      kindRaw === 'line' || kindRaw === 'accent' || kindRaw === 'rect' ? kindRaw : 'rect';
    const opacity =
      body.opacity === undefined || body.opacity === null
        ? undefined
        : clampOpacity(body.opacity, 1);
    return {
      ...base,
      type: 'SHAPE',
      fill:
        typeof body.fill === 'string' && body.fill.trim()
          ? body.fill
          : typeof body.backgroundColor === 'string' && body.backgroundColor.trim()
            ? body.backgroundColor
            : '#C4A35A',
      shapeKind,
      ...(typeof body.borderRadius === 'number' && Number.isFinite(body.borderRadius)
        ? { borderRadius: Math.max(0, Math.round(body.borderRadius)) }
        : {}),
      ...(opacity !== undefined ? { opacity } : {}),
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
      ...(el.fontFamily ? { fontFamily: el.fontFamily } : {}),
      ...(el.lineHeight !== undefined ? { lineHeight: el.lineHeight } : {}),
      ...(el.letterSpacing !== undefined ? { letterSpacing: el.letterSpacing } : {}),
      ...(el.opacity !== undefined ? { opacity: el.opacity } : {}),
    };
  }
  if (el.type === 'IMAGE') {
    return {
      ...base,
      assetId: el.assetId && isMediaAssetUuid(el.assetId) ? el.assetId : null,
      ...(el.role ? { role: el.role } : {}),
      ...(el.crop ? { crop: el.crop } : {}),
      ...(el.objectPosition ? { objectPosition: el.objectPosition } : {}),
      ...(el.objectFit ? { objectFit: el.objectFit } : {}),
      ...(el.lockAspectRatio !== undefined ? { lockAspectRatio: el.lockAspectRatio } : {}),
      ...(el.opacity !== undefined ? { opacity: el.opacity } : {}),
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
  if (el.type === 'SHAPE') {
    return {
      ...base,
      fill: el.fill,
      ...(el.shapeKind ? { shapeKind: el.shapeKind } : {}),
      ...(el.borderRadius !== undefined ? { borderRadius: el.borderRadius } : {}),
      ...(el.opacity !== undefined ? { opacity: el.opacity } : {}),
    };
  }
  return {
    ...base,
    label: el.label,
    backgroundColor: el.backgroundColor,
    textColor: el.textColor,
    ...(el.ctaStyle ? { ctaStyle: el.ctaStyle } : {}),
    ...(el.fontSize !== undefined ? { fontSize: el.fontSize } : {}),
    ...(el.fontWeight !== undefined ? { fontWeight: el.fontWeight } : {}),
    ...(el.fontFamily ? { fontFamily: el.fontFamily } : {}),
    ...(el.align ? { align: el.align } : {}),
    ...(el.borderRadius !== undefined ? { borderRadius: el.borderRadius } : {}),
    ...(el.padding !== undefined ? { padding: el.padding } : {}),
    ...(el.opacity !== undefined ? { opacity: el.opacity } : {}),
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
    ...(post.campaignContextId ? { campaignContextId: post.campaignContextId } : {}),
    ...(post.generationContextId ? { generationContextId: post.generationContextId } : {}),
    ...(post.createdAt ? { createdAt: post.createdAt } : {}),
    ...(post.updatedAt ? { updatedAt: post.updatedAt } : {}),
    ...(post.compositionStrategy ? { compositionStrategy: post.compositionStrategy } : {}),
    ...(post.compositionPrimitive
      ? { compositionPrimitive: post.compositionPrimitive }
      : post.generationMeta &&
          typeof post.generationMeta === 'object' &&
          post.generationMeta.creative_plan &&
          typeof (post.generationMeta.creative_plan as { composition?: unknown }).composition === 'string'
        ? {
            compositionPrimitive: (post.generationMeta.creative_plan as { composition: string })
              .composition,
          }
        : {}),
    ...(post.overlayStrategy ? { overlayStrategy: post.overlayStrategy } : {}),
    ...(post.textAlign ? { textAlign: post.textAlign } : {}),
    ...(post.safeTextZone ? { safeTextZone: post.safeTextZone } : {}),
    ...(post.ctaStrategy ? { ctaStrategy: post.ctaStrategy } : {}),
    ...(post.creativePlan ? { creativePlan: post.creativePlan } : {}),
    ...(post.compositionBlueprint ? { compositionBlueprint: post.compositionBlueprint } : {}),
    ...(post.compositionFamily ? { compositionFamily: post.compositionFamily } : {}),
    ...(post.imageCrop ? { imageCrop: post.imageCrop } : {}),
    ...(post.compositionType ? { compositionType: post.compositionType } : {}),
    ...(post.planGeometryLocked ? { planGeometryLocked: true } : {}),
    ...(post.generationLifecycle === 'ready' || post.generationLifecycle === 'error'
      ? { generationLifecycle: post.generationLifecycle }
      : {}),
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
  const generationMeta =
    body.generationMeta && typeof body.generationMeta === 'object' && !Array.isArray(body.generationMeta)
      ? (body.generationMeta as Record<string, unknown>)
      : null;
  const finishedAd =
    generationMeta?.production_mode === 'finished_ad' ||
    generationMeta?.production_mode === 'editable_finished_ad' ||
    generationMeta?.production_mode === 'golden_native_v1' ||
    generationMeta?.generated_by === 'creative_director_generate_ad';
  const editableFinishedAd =
    generationMeta?.production_mode === 'editable_finished_ad' ||
    generationMeta?.production_mode === 'golden_native_v1' ||
    (Boolean(
      generationMeta?.gpt_image &&
        typeof generationMeta.gpt_image === 'object' &&
        !Array.isArray(generationMeta.gpt_image) &&
        (generationMeta.gpt_image as Record<string, unknown>).editable_layers === true,
    ) &&
      Boolean(generationMeta?.design_spec));
  const coverRaw =
    typeof body.coverAssetId === 'string'
      ? body.coverAssetId
      : typeof body.cover_asset_id === 'string'
        ? body.cover_asset_id
        : null;
  const coverId = coverRaw && isMediaAssetUuid(coverRaw) ? coverRaw.trim() : null;
  const gptLocal =
    generationMeta?.gpt_image &&
    typeof generationMeta.gpt_image === 'object' &&
    !Array.isArray(generationMeta.gpt_image)
      ? (generationMeta.gpt_image as Record<string, unknown>).local_asset_id
      : null;
  // Prefer coverAssetId (revision updates it) over stale gpt_image.local_asset_id.
  const finishedAssetId =
    coverId ||
    (typeof gptLocal === 'string' && isMediaAssetUuid(gptLocal) ? gptLocal.trim() : null) ||
    (() => {
      const img = parsedElements.find(
        (el): el is SocialImageElement =>
          el.type === 'IMAGE' && Boolean(el.assetId && isMediaAssetUuid(el.assetId)),
      );
      return img?.assetId && isMediaAssetUuid(img.assetId) ? img.assetId : null;
    })();
  const hasCopy = Boolean(headline.trim() || caption.trim());
  // Legacy finished-ad raster: always exactly one full-bleed IMAGE.
  // Editable finished-ad: preserve layered elements (+ design_spec) on reload.
  const elements = ensureUniqueElementIds(
    finishedAd && !editableFinishedAd
      ? finishedAssetId
        ? [
            {
              id: 'img-finished-ad',
              type: 'IMAGE' as const,
              role: 'background' as const,
              assetId: finishedAssetId,
              x: 0,
              y: 0,
              width,
              height,
              zIndex: 0,
            },
          ]
        : []
      : parsedElements.length > 0
        ? parsedElements
        : hasCopy
          ? createDefaultElements(width, height, { headline, caption })
          : [],
  );
  const lifecycleRaw = body.generationLifecycle ?? body.generation_lifecycle;
  const generationLifecycle: SocialPostGenerationLifecycle | null =
    lifecycleRaw === 'ready' || lifecycleRaw === 'error' || lifecycleRaw === 'generating' || lifecycleRaw === 'creating'
      ? lifecycleRaw
      : parsedElements.length || hasCopy || finishedAd
        ? 'ready'
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
    headline: finishedAd ? '' : headlineFromElements(elements) || headline,
    description: typeof body.description === 'string' ? body.description : '',
    caption: finishedAd ? '' : captionFromElements(elements) || caption,
    coverAssetId: finishedAd ? finishedAssetId || coverId : coverId,
    linkedProjectId:
      typeof linkedRaw === 'string' && linkedRaw.trim() ? linkedRaw.trim() : null,
    elements,
    generationMeta,
    campaignContextId: asOptionalId(
      body.campaignContextId ??
        body.campaign_context_id ??
        generationMeta?.campaign_context_id,
    ),
    generationContextId: asOptionalId(body.generationContextId ?? body.generation_context_id),
    createdAt: typeof body.createdAt === 'string' ? body.createdAt : typeof body.created_at === 'string' ? body.created_at : null,
    updatedAt: typeof body.updatedAt === 'string' ? body.updatedAt : typeof body.updated_at === 'string' ? body.updated_at : null,
    compositionStrategy: typeof body.compositionStrategy === 'string' ? body.compositionStrategy : null,
    compositionPrimitive:
      typeof body.compositionPrimitive === 'string' ? body.compositionPrimitive : null,
    overlayStrategy: typeof body.overlayStrategy === 'string' ? body.overlayStrategy : null,
    textAlign:
      body.textAlign === 'left' || body.textAlign === 'center' || body.textAlign === 'right'
        ? body.textAlign
        : null,
    safeTextZone: typeof body.safeTextZone === 'string' ? body.safeTextZone : null,
    ctaStrategy: typeof body.ctaStrategy === 'string' ? body.ctaStrategy : null,
    creativePlan:
      body.creativePlan && typeof body.creativePlan === 'object' && !Array.isArray(body.creativePlan)
        ? (body.creativePlan as Record<string, unknown>)
        : null,
    compositionBlueprint:
      (body.compositionBlueprint && typeof body.compositionBlueprint === 'object' && !Array.isArray(body.compositionBlueprint)
        ? (body.compositionBlueprint as Record<string, unknown>)
        : body.generationMeta &&
            typeof body.generationMeta === 'object' &&
            (body.generationMeta as { composition_blueprint?: unknown }).composition_blueprint &&
            typeof (body.generationMeta as { composition_blueprint?: unknown }).composition_blueprint === 'object'
          ? ((body.generationMeta as { composition_blueprint: Record<string, unknown> }).composition_blueprint)
          : null),
    compositionFamily:
      typeof body.compositionFamily === 'string'
        ? body.compositionFamily
        : typeof body.composition_family === 'string'
          ? body.composition_family
          : null,
    imageCrop:
      body.imageCrop && typeof body.imageCrop === 'object' && !Array.isArray(body.imageCrop)
        ? (body.imageCrop as Record<string, unknown>)
        : body.image_crop && typeof body.image_crop === 'object' && !Array.isArray(body.image_crop)
          ? (body.image_crop as Record<string, unknown>)
          : null,
    compositionType:
      typeof body.compositionType === 'string'
        ? body.compositionType
        : typeof body.composition_type === 'string'
          ? body.composition_type
          : null,
    planGeometryLocked: body.planGeometryLocked === true || body.plan_geometry_locked === true,
    generationLifecycle,
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
 * After deleting a Gönderiler post: keep current selection if it still exists;
 * otherwise next, else previous, else empty.
 * A B C D / delete B → C; delete D → C; delete A → B.
 */
export function nextSelectedPostIdAfterDelete(
  posts: Array<{ id: string }>,
  deletedId: string,
  currentSelectedId: string | null | undefined,
): string | null {
  const index = posts.findIndex((p) => p.id === deletedId);
  if (index < 0) return currentSelectedId || null;
  if (currentSelectedId && currentSelectedId !== deletedId) return currentSelectedId;
  const remaining = posts.filter((p) => p.id !== deletedId);
  if (!remaining.length) return null;
  return remaining[index]?.id ?? remaining[index - 1]?.id ?? remaining[0]?.id ?? null;
}

/** Remove one post record (canvas, blueprint, campaign metadata). Never touches Assets/Drive. */
export function deleteSocialPost<T extends { id: string }>(
  posts: T[],
  postId: string,
  selectedPostId: string | null | undefined,
): { posts: T[]; selectedPostId: string | null; deleted: T | null } {
  const deleted = posts.find((p) => p.id === postId) ?? null;
  if (!deleted) return { posts, selectedPostId: selectedPostId ?? null, deleted: null };
  return {
    posts: posts.filter((p) => p.id !== postId),
    selectedPostId: nextSelectedPostIdAfterDelete(posts, postId, selectedPostId),
    deleted,
  };
}

export function isInFlightGenerationPost(post: SocialPost | null | undefined): boolean {
  if (!post) return false;
  return post.generationLifecycle === 'creating' || post.generationLifecycle === 'generating';
}

/** Finished-ad raster posts: empty headline by design — must still beat stale draft restore. */
export function isFinishedAdSocialPost(post: SocialPost | null | undefined): boolean {
  if (!post) return false;
  const meta =
    post.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  return (
    meta?.production_mode === 'finished_ad' ||
    meta?.production_mode === 'editable_finished_ad' ||
    meta?.production_mode === 'golden_native_v1' ||
    meta?.generated_by === 'creative_director_generate_ad'
  );
}

export function isPlaceholderSocialPost(post: SocialPost | null | undefined): boolean {
  if (!post) return false;
  if (isInFlightGenerationPost(post)) return true;
  if (isFinishedAdSocialPost(post)) return false;
  const headline = (headlineFromElements(post.elements) || post.headline || '').trim();
  const hasGeneratedMeta = Boolean(
    post.generationMeta &&
      typeof post.generationMeta === 'object' &&
      (post.generationMeta.content_package || post.generationMeta.creative_plan),
  );
  return headline === PLACEHOLDER_HEADLINE && !post.coverAssetId && !hasGeneratedMeta;
}

export function isCompletedGeneratedPost(post: SocialPost | null | undefined): boolean {
  if (!post || isInFlightGenerationPost(post) || post.generationLifecycle === 'error') return false;
  const meta = post.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  const hasCover = Boolean(post.coverAssetId && isMediaAssetUuid(post.coverAssetId));
  // Finished ads bake copy into the raster — empty headline must still count as completed.
  if (isFinishedAdSocialPost(post) && hasCover) return true;
  const headline = (headlineFromElements(post.elements) || post.headline || '').trim();
  if (!headline || headline === PLACEHOLDER_HEADLINE) return false;
  const hasPackage = Boolean(meta?.content_package);
  const hasPlan = Boolean(post.creativePlan || meta?.creative_plan);
  const hasBlueprint = Boolean(post.compositionBlueprint || meta?.composition_blueprint);
  const hasText = post.elements.some(
    (el) => el.type === 'TEXT' && typeof el.content === 'string' && el.content.trim().length > 0,
  );
  const isIdeogramFlat = meta?.provider === 'ideogram' && hasCover;
  return hasPackage || hasPlan || hasBlueprint || (hasCover && hasText) || isIdeogramFlat;
}

/** CREATE response is usable even if headline/meta gates are incomplete. */
export function hasAppliedCreateResult(post: SocialPost | null | undefined): boolean {
  if (!post || isInFlightGenerationPost(post) || post.generationLifecycle === 'error') return false;
  if (isCompletedGeneratedPost(post)) return true;
  if (post.coverAssetId && isMediaAssetUuid(post.coverAssetId)) return true;
  const hasCopy = post.elements.some((el) => {
    if (el.type === 'TEXT' && typeof el.content === 'string' && el.content.trim()) return true;
    if (el.type === 'BUTTON' && typeof el.label === 'string' && el.label.trim()) return true;
    return false;
  });
  if (hasCopy) return true;
  const meta = post.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  return Boolean(meta?.content_package || meta?.creative_plan || meta?.composition_blueprint);
}

export function stripInFlightPostsForPersist(posts: SocialPost[]): SocialPost[] {
  return posts.filter((p) => !isInFlightGenerationPost(p));
}

export function normalizeSelectedPostId(
  value: string | null | undefined,
  posts: Array<{ id: string }>,
): string | null {
  const id = typeof value === 'string' ? value.trim() : '';
  if (!id) return posts[0]?.id ?? null;
  if (posts.some((p) => p.id === id)) return id;
  return posts[0]?.id ?? null;
}

/**
 * Hydrate must not wipe an in-flight CREATE or a newer completed generation
 * with a stale draft (empty posts[] / older placeholder).
 */
export type SmbSelectedIdentity = {
  postId: string | null;
  campaignId: string | null;
  coverAssetId: string | null;
  masterFinishedAdAssetId: string | null;
};

export const SMB_SELECTED_IDENTITY_STORAGE_PREFIX = 'ih.cs.smb.selectedIdentity:';

export function smbSelectedIdentityStorageKey(projectId: string | null | undefined): string {
  return `${SMB_SELECTED_IDENTITY_STORAGE_PREFIX}${projectId && projectId.trim() ? projectId.trim() : 'none'}`;
}

export function parseSmbSelectedIdentity(raw: unknown): SmbSelectedIdentity | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const postId = typeof body.postId === 'string' && body.postId.trim() ? body.postId.trim() : null;
  const campaignId =
    typeof body.campaignId === 'string' && body.campaignId.trim() ? body.campaignId.trim() : null;
  const coverAssetId =
    typeof body.coverAssetId === 'string' && isMediaAssetUuid(body.coverAssetId)
      ? body.coverAssetId.trim()
      : null;
  const masterFinishedAdAssetId =
    typeof body.masterFinishedAdAssetId === 'string' && isMediaAssetUuid(body.masterFinishedAdAssetId)
      ? body.masterFinishedAdAssetId.trim()
      : null;
  if (!postId && !campaignId && !coverAssetId && !masterFinishedAdAssetId) return null;
  return { postId, campaignId, coverAssetId, masterFinishedAdAssetId };
}

export function readSmbSelectedIdentity(projectId: string | null | undefined): SmbSelectedIdentity | null {
  if (typeof sessionStorage === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem(smbSelectedIdentityStorageKey(projectId));
    if (!raw) return null;
    return parseSmbSelectedIdentity(JSON.parse(raw) as unknown);
  } catch {
    return null;
  }
}

export function writeSmbSelectedIdentity(
  projectId: string | null | undefined,
  identity: SmbSelectedIdentity | null,
): void {
  if (typeof sessionStorage === 'undefined') return;
  const key = smbSelectedIdentityStorageKey(projectId);
  try {
    if (!identity || (!identity.postId && !identity.coverAssetId && !identity.campaignId)) {
      sessionStorage.removeItem(key);
      return;
    }
    sessionStorage.setItem(key, JSON.stringify(identity));
  } catch {
    /* quota / private mode — draft persist remains the fallback */
  }
}

function campaignIdFromPost(post: {
  campaignContextId?: string | null;
  generationMeta?: Record<string, unknown> | null;
}): string | null {
  if (typeof post.campaignContextId === 'string' && post.campaignContextId.trim()) {
    return post.campaignContextId.trim();
  }
  const meta = post.generationMeta;
  const raw = meta?.campaign_context_id ?? meta?.campaign_id;
  return typeof raw === 'string' && raw.trim() ? raw.trim() : null;
}

function masterFinishedAdIdFromPost(post: {
  generationMeta?: Record<string, unknown> | null;
}): string | null {
  const meta = post.generationMeta;
  const raw = meta?.master_finished_ad_asset_id ?? meta?.master_asset_id;
  return typeof raw === 'string' && isMediaAssetUuid(raw) ? raw.trim() : null;
}

/**
 * Restore the exact filmstrip selection. Never auto-pick latest / posts[0]
 * when a persisted identity still matches.
 */
export function resolvePersistedSelectedPostId(input: {
  posts: Array<{
    id: string;
    coverAssetId?: string | null;
    campaignContextId?: string | null;
    generationMeta?: Record<string, unknown> | null;
  }>;
  draftSelectedPostId?: string | null;
  coverAssetId?: string | null;
  identity?: SmbSelectedIdentity | null;
  localSelectedPostId?: string | null;
  preferLocalSelection?: boolean;
}): string | null {
  const posts = input.posts;
  if (!posts.length) return null;
  const hasId = (id: string | null | undefined): id is string =>
    Boolean(id && posts.some((p) => p.id === id));

  if (hasId(input.identity?.postId)) return input.identity!.postId;
  if (hasId(input.draftSelectedPostId)) return input.draftSelectedPostId;

  const cover = input.identity?.coverAssetId || input.coverAssetId || null;
  if (cover) {
    const byCover = posts.find((p) => p.coverAssetId === cover);
    if (byCover) return byCover.id;
  }

  const campaign = input.identity?.campaignId || null;
  if (campaign) {
    const byCampaign = posts.find((p) => campaignIdFromPost(p) === campaign);
    if (byCampaign) return byCampaign.id;
  }

  const master = input.identity?.masterFinishedAdAssetId || null;
  if (master) {
    const byMaster = posts.find((p) => masterFinishedAdIdFromPost(p) === master);
    if (byMaster) return byMaster.id;
  }

  if (input.preferLocalSelection !== false && hasId(input.localSelectedPostId)) {
    return input.localSelectedPostId;
  }

  return posts[0]?.id ?? null;
}

export function identityFromSocialPost(post: SocialPost | null | undefined): SmbSelectedIdentity | null {
  if (!post) return null;
  return {
    postId: post.id,
    campaignId: campaignIdFromPost(post),
    coverAssetId: post.coverAssetId && isMediaAssetUuid(post.coverAssetId) ? post.coverAssetId : null,
    masterFinishedAdAssetId: masterFinishedAdIdFromPost(post),
  };
}

export function mergeHydratedPostsWithLocal(input: {
  incoming: SocialPost[];
  local: SocialPost[];
  deletedIds: Set<string>;
  generating: boolean;
  incomingSelectedPostId?: string | null;
  localSelectedPostId?: string | null;
  identity?: SmbSelectedIdentity | null;
  coverAssetId?: string | null;
  /** False on first refresh hydrate so DEFAULT p1 cannot steal the canvas. */
  preferLocalSelection?: boolean;
}): { posts: SocialPost[]; selectedPostId: string | null } {
  const incoming = input.incoming.filter((p) => !input.deletedIds.has(p.id));
  const local = input.local.filter((p) => !input.deletedIds.has(p.id));
  const localInFlight = local.filter((p) => isInFlightGenerationPost(p));
  const localCompleted = local.filter((p) => isCompletedGeneratedPost(p));

  if (input.generating || localInFlight.length) {
    const byId = new Map<string, SocialPost>();
    for (const post of incoming) byId.set(post.id, post);
    for (const post of localCompleted) byId.set(post.id, post);
    for (const post of localInFlight) byId.set(post.id, post);
    const ordered: SocialPost[] = [];
    const seen = new Set<string>();
    for (const post of local) {
      const next = byId.get(post.id);
      if (next && !seen.has(next.id)) {
        ordered.push(next);
        seen.add(next.id);
      }
    }
    for (const post of incoming) {
      if (!seen.has(post.id)) {
        ordered.push(post);
        seen.add(post.id);
      }
    }
    const selected =
      resolvePersistedSelectedPostId({
        posts: ordered,
        draftSelectedPostId: input.incomingSelectedPostId,
        coverAssetId: input.coverAssetId,
        identity: input.identity,
        localSelectedPostId: input.localSelectedPostId,
        preferLocalSelection: input.preferLocalSelection !== false,
      }) ??
      localInFlight[0]?.id ??
      ordered[0]?.id ??
      null;
    return { posts: ordered, selectedPostId: selected };
  }

  if (!incoming.length) {
    return { posts: [], selectedPostId: null };
  }

  const incomingIds = new Set(incoming.map((p) => p.id));
  const extraLocal = input.generating
    ? localCompleted.filter((p) => !incomingIds.has(p.id))
    : [];
  const merged = incoming.map((post) => {
    const existing = local.find((l) => l.id === post.id);
    if (existing && isFinishedAdSocialPost(existing) && !isFinishedAdSocialPost(post)) {
      return existing;
    }
    if (existing && isCompletedGeneratedPost(existing) && !isCompletedGeneratedPost(post)) {
      return existing;
    }
    if (existing && isPlaceholderSocialPost(post) && !isPlaceholderSocialPost(existing)) {
      return existing;
    }
    const existingMeta =
      existing?.generationMeta && typeof existing.generationMeta === 'object'
        ? existing.generationMeta
        : null;
    const incomingMeta =
      post.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
    if (
      existing &&
      existingMeta?.production_mode === 'editable_finished_ad' &&
      incomingMeta?.production_mode === 'finished_ad' &&
      existing.elements.some((el) => el.type === 'TEXT') &&
      !post.elements.some((el) => el.type === 'TEXT')
    ) {
      return existing;
    }
    return post;
  });
  const posts = [...merged, ...extraLocal];
  // Prefer local finished-ad / completed selection over stale draft selectedPostId
  // (otherwise "New social post" siblings steal the canvas after Oluştur).
  // On refresh, caller must pass preferLocalSelection=false so DEFAULT p1 cannot win.
  const localSelectedProtected =
    input.preferLocalSelection !== false &&
    Boolean(
      input.localSelectedPostId &&
        local.some(
          (p) =>
            p.id === input.localSelectedPostId &&
            (isFinishedAdSocialPost(p) || isCompletedGeneratedPost(p)),
        ),
    ) &&
    posts.some((p) => p.id === input.localSelectedPostId);
  const selected = localSelectedProtected
    ? input.localSelectedPostId!
    : resolvePersistedSelectedPostId({
        posts,
        draftSelectedPostId: input.incomingSelectedPostId,
        coverAssetId: input.coverAssetId,
        identity: input.identity,
        localSelectedPostId: input.localSelectedPostId,
        preferLocalSelection: input.preferLocalSelection !== false,
      });
  return { posts, selectedPostId: selected };
}

/**
 * CREATE result must patch the in-flight post slot in place.
 * createdPostId === generationTargetPostId === patchedPostId — remap server ids onto the inflight slot.
 */
export function mergeCreateGenerationResult(input: {
  localPosts: SocialPost[];
  appliedPosts: SocialPost[];
  inflightId: string | null;
  appliedSelectedPostId: string | null;
  deletedIds: Set<string>;
}): { posts: SocialPost[]; selectedPostId: string | null; generated: SocialPost | null } {
  const inflightId = input.inflightId;
  const appliedSelectedPostId = input.appliedSelectedPostId;
  const applied = input.appliedPosts.filter((p) => !input.deletedIds.has(p.id));
  const localSiblings = input.localPosts.filter(
    (p) => p.id !== inflightId && !input.deletedIds.has(p.id),
  );
  const localIds = new Set(localSiblings.map((p) => p.id));

  let generated =
    (inflightId ? applied.find((p) => p.id === inflightId) : null) ??
    (appliedSelectedPostId
      ? applied.find((p) => p.id === appliedSelectedPostId && !localIds.has(p.id))
      : null) ??
    applied.find((p) => !localIds.has(p.id)) ??
    null;

  if (generated && inflightId && generated.id !== inflightId) {
    generated = { ...generated, id: inflightId };
  }

  const readyGenerated = generated
    ? {
        ...generated,
        generationLifecycle: 'ready' as SocialPostGenerationLifecycle,
        linkedProjectId: generated.linkedProjectId,
      }
    : null;

  const skipIds = new Set<string>();
  if (inflightId) skipIds.add(inflightId);
  if (appliedSelectedPostId && readyGenerated && appliedSelectedPostId !== readyGenerated.id) {
    skipIds.add(appliedSelectedPostId);
  }

  const siblingFromApplied = applied.filter(
    (p) => !skipIds.has(p.id) && !input.deletedIds.has(p.id),
  );

  const posts: SocialPost[] = [];
  const seen = new Set<string>();
  for (const local of input.localPosts) {
    if (input.deletedIds.has(local.id)) continue;
    if (local.id === inflightId) {
      if (readyGenerated && !seen.has(readyGenerated.id)) {
        posts.push(readyGenerated);
        seen.add(readyGenerated.id);
      }
      continue;
    }
    const next = siblingFromApplied.find((p) => p.id === local.id) ?? local;
    if (!seen.has(next.id)) {
      posts.push(next);
      seen.add(next.id);
    }
  }
  for (const post of siblingFromApplied) {
    if (!seen.has(post.id)) {
      posts.push(post);
      seen.add(post.id);
    }
  }
  if (readyGenerated && !seen.has(readyGenerated.id)) {
    posts.push(readyGenerated);
  }
  if (!posts.length) {
    return {
      posts: localSiblings,
      selectedPostId: localSiblings[0]?.id ?? null,
      generated: readyGenerated,
    };
  }

  return {
    posts,
    selectedPostId: readyGenerated?.id ?? inflightId ?? appliedSelectedPostId ?? posts[0]?.id ?? null,
    generated: readyGenerated,
  };
}

/**
 * Cover-image-only drafts → one post with default TEXT/BUTTON elements + cover Asset ID.
 * Existing posts[] drafts are returned as-is (with element parse/migration).
 * Explicit posts: [] is last-post-deleted empty state — not reseeded from DEFAULT_POSTS.
 */
export function hydrateSocialPostsFromDraft(input: {
  posts?: unknown;
  coverAssetId?: string | null;
  linkedProjectId?: string | null;
  selectedPostId?: string | null;
  selectedIdentity?: SmbSelectedIdentity | null;
  seedDefaults?: boolean;
}): { posts: SocialPost[]; selectedPostId: string | null } {
  const linked = input.linkedProjectId ?? null;
  const parsed = parseSocialPosts(input.posts, linked);
  if (parsed.length) {
    const withOwnCover = parsed.map((p) => ({
      ...p,
      linkedProjectId: p.linkedProjectId || linked,
    }));
    const selected = resolvePersistedSelectedPostId({
      posts: withOwnCover,
      draftSelectedPostId: input.selectedPostId,
      coverAssetId: input.coverAssetId,
      identity: input.selectedIdentity,
      preferLocalSelection: false,
    });
    const withCover = withOwnCover.map((p) => {
      if (p.coverAssetId) return p;
      if (p.id === selected && input.coverAssetId && isMediaAssetUuid(input.coverAssetId)) {
        return { ...p, coverAssetId: input.coverAssetId };
      }
      return p;
    });
    return { posts: withCover, selectedPostId: selected };
  }

  // Explicit posts: [] means the last Gönderi was deleted — do not reseed defaults.
  if (Array.isArray(input.posts)) {
    return { posts: [], selectedPostId: null };
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
