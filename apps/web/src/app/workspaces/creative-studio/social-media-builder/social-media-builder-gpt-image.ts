/**
 * GPT Image SMB helpers — composed raster + editable OS layers when present.
 */

import { getCreativeStudioMediaContentUrl } from '@/lib/api/creative-studio';

import {
  ensureUniqueElementIds,
  type SocialElement,
} from './social-media-builder-elements';
import { mintCreatePostId, resolveFormatSize, type FormatPresetKey, type SocialPost } from './social-media-builder-model';
import { isMediaAssetUuid } from '../_components/cs-image-ref';

export const GPT_IMAGE_STAGES = [
  'gptImageBrief',
  'gptImageSource',
  'gptImageGenerating',
  'gptImageSaving',
] as const;

export function asFormatPreset(value: string | null | undefined): FormatPresetKey {
  if (
    value === 'square' ||
    value === 'portrait' ||
    value === 'landscape' ||
    value === 'story' ||
    value === 'reelsCover' ||
    value === 'carousel'
  ) {
    return value;
  }
  return 'portrait';
}

export function gptImagePreviewUrl(
  localAssetId: string,
  localAssetUrl: string,
  linkedProjectId: string | null,
): string {
  if (localAssetUrl.startsWith('http') || localAssetUrl.startsWith('/')) {
    if (linkedProjectId && localAssetUrl.includes('/creative-studio/media/assets/')) {
      return getCreativeStudioMediaContentUrl(localAssetId, {
        linked_project_id: linkedProjectId,
      });
    }
    return localAssetUrl;
  }
  return getCreativeStudioMediaContentUrl(localAssetId, {
    linked_project_id: linkedProjectId,
  });
}

function asSocialElements(raw: unknown[] | null | undefined): SocialElement[] {
  if (!Array.isArray(raw) || !raw.length) return [];
  const out: SocialElement[] = [];
  for (const row of raw) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) continue;
    const el = row as Record<string, unknown>;
    const type = String(el.type ?? '').toUpperCase();
    if (type !== 'TEXT' && type !== 'IMAGE' && type !== 'BUTTON' && type !== 'METRIC_GROUP' && type !== 'SHAPE') continue;
    out.push({ ...el, type } as SocialElement);
  }
  return ensureUniqueElementIds(out);
}

function ensureBackgroundLayer(
  elements: SocialElement[],
  compositionBaseAssetId: string | null | undefined,
  width: number,
  height: number,
): SocialElement[] {
  const hasBackground = elements.some(
    (el) => el.type === 'IMAGE' && (el.role === 'background' || el.id === 'background-gpt-image'),
  );
  if (hasBackground || !compositionBaseAssetId || !isMediaAssetUuid(compositionBaseAssetId)) {
    return elements;
  }
  const background: SocialElement = {
    id: 'background-gpt-image',
    type: 'IMAGE',
    role: 'background',
    assetId: compositionBaseAssetId,
    x: 0,
    y: 0,
    width,
    height,
    zIndex: 0,
  };
  return [background, ...elements.map((el) => ({ ...el, zIndex: Math.max(1, (el.zIndex ?? 1)) }))];
}

export function isFinishedAdCanvasMeta(
  meta: Record<string, unknown> | null | undefined,
): boolean {
  if (!meta || typeof meta !== 'object') return false;
  return (
    meta.production_mode === 'finished_ad' ||
    meta.production_mode === 'editable_finished_ad' ||
    meta.generated_by === 'creative_director_generate_ad'
  );
}

export function isEditableFinishedAdMeta(
  meta: Record<string, unknown> | null | undefined,
): boolean {
  if (!meta || typeof meta !== 'object') return false;
  if (meta.production_mode === 'editable_finished_ad') return true;
  const gpt =
    meta.gpt_image && typeof meta.gpt_image === 'object' && !Array.isArray(meta.gpt_image)
      ? (meta.gpt_image as Record<string, unknown>)
      : null;
  return Boolean(gpt?.editable_layers === true && meta.design_spec);
}

export function isFinishedAdCanvasPost(post: SocialPost | null | undefined): boolean {
  return isFinishedAdCanvasMeta(post?.generationMeta ?? null);
}

export function isEditableFinishedAdPost(post: SocialPost | null | undefined): boolean {
  return isEditableFinishedAdMeta(post?.generationMeta ?? null);
}

/** Sole full-bleed IMAGE for finished-ad production — never default TEXT/CTA/logo layers. */
export function createFinishedAdCanvasPost(input: {
  localAssetId: string;
  linkedProjectId: string;
  formatPreset: FormatPresetKey;
  instruction: string;
  model: string;
  sessionId: string;
  campaignContextId: string | null;
  sourceAssetId: string | null;
  index: number;
  canvasWidth?: number | null;
  canvasHeight?: number | null;
  compositionWarnings?: string[] | null;
  provider?: string | null;
  logoAssetId?: string | null;
  interiorAssetId?: string | null;
  /** Editable layered mode — hydrate from design_spec / editable_layers. */
  editableFinishedAd?: boolean;
  designSpec?: Record<string, unknown> | null;
  editableLayers?: unknown[] | null;
  masterBackgroundAssetId?: string | null;
  finishedAdRasterAssetId?: string | null;
}): SocialPost {
  return createFlattenedGptImagePost({
    ...input,
    headline: '',
    layers: input.editableFinishedAd ? input.editableLayers ?? null : null,
    compositionBaseAssetId: input.editableFinishedAd
      ? input.masterBackgroundAssetId ?? input.interiorAssetId ?? null
      : null,
    finishedAd: true,
    editableFinishedAd: Boolean(input.editableFinishedAd),
    designSpec: input.designSpec,
    masterBackgroundAssetId: input.masterBackgroundAssetId,
    finishedAdRasterAssetId: input.finishedAdRasterAssetId,
    provider: input.provider,
    logoAssetId: input.logoAssetId,
    interiorAssetId: input.interiorAssetId,
  });
}

/** GPT Image creative as a NEW SMB post. Uses editable layers when OS composition returns them. */
export function createFlattenedGptImagePost(input: {
  localAssetId: string;
  linkedProjectId: string;
  formatPreset: FormatPresetKey;
  instruction: string;
  model: string;
  sessionId: string;
  campaignContextId: string | null;
  sourceAssetId: string | null;
  headline?: string;
  index: number;
  canvasWidth?: number | null;
  canvasHeight?: number | null;
  layers?: unknown[] | null;
  compositionBaseAssetId?: string | null;
  compositionWarnings?: string[] | null;
  /** Finished-ad raster: ignore OS layers; exactly one full-bleed background IMAGE. */
  finishedAd?: boolean;
  /** Layered editable finished-ad — master background + overlays from design_spec. */
  editableFinishedAd?: boolean;
  designSpec?: Record<string, unknown> | null;
  masterBackgroundAssetId?: string | null;
  finishedAdRasterAssetId?: string | null;
  provider?: string | null;
  logoAssetId?: string | null;
  interiorAssetId?: string | null;
}): SocialPost {
  const preset = input.formatPreset;
  const size = resolveFormatSize(preset);
  const width = input.canvasWidth && input.canvasWidth > 0 ? input.canvasWidth : size.w;
  const height = input.canvasHeight && input.canvasHeight > 0 ? input.canvasHeight : size.h;
  const finishedAd = Boolean(input.finishedAd);
  const editableFinishedAd = Boolean(input.editableFinishedAd) && finishedAd;
  const masterBg =
    (input.masterBackgroundAssetId && isMediaAssetUuid(input.masterBackgroundAssetId)
      ? input.masterBackgroundAssetId
      : null) ||
    (input.compositionBaseAssetId && isMediaAssetUuid(input.compositionBaseAssetId)
      ? input.compositionBaseAssetId
      : null) ||
    (input.interiorAssetId && isMediaAssetUuid(input.interiorAssetId) ? input.interiorAssetId : null);

  const layeredRaw = editableFinishedAd
    ? asSocialElements(input.layers)
    : finishedAd
      ? []
      : asSocialElements(input.layers);
  let layered =
    layeredRaw.length > 0
      ? ensureBackgroundLayer(layeredRaw, masterBg || input.compositionBaseAssetId, width, height)
      : layeredRaw;

  // Ensure locked master background for editable finished-ad even when layers omit it.
  if (editableFinishedAd && masterBg) {
    const hasBg = layered.some(
      (el) => el.type === 'IMAGE' && (el.role === 'background' || el.id === 'master_background'),
    );
    if (!hasBg) {
      layered = [
        {
          id: 'master_background',
          type: 'IMAGE',
          role: 'background',
          assetId: masterBg,
          x: 0,
          y: 0,
          width,
          height,
          zIndex: 0,
          objectFit: 'cover',
        },
        ...layered.map((el) => ({ ...el, zIndex: Math.max(1, el.zIndex ?? 1) })),
      ];
    } else {
      layered = layered.map((el) =>
        el.type === 'IMAGE' && (el.role === 'background' || el.id === 'master_background')
          ? { ...el, id: 'master_background', role: 'background' as const, assetId: masterBg }
          : el,
      );
    }
  }

  const coverId = editableFinishedAd
    ? masterBg || input.localAssetId
    : finishedAd
      ? input.localAssetId
      : (input.compositionBaseAssetId && isMediaAssetUuid(input.compositionBaseAssetId)
          ? input.compositionBaseAssetId
          : null) || input.localAssetId;
  const soleFinishedImage: SocialElement = {
    id: 'img-finished-ad',
    type: 'IMAGE',
    role: 'background',
    assetId: input.localAssetId,
    x: 0,
    y: 0,
    width,
    height,
    zIndex: 0,
  };
  const elements: SocialElement[] =
    editableFinishedAd && layered.length > 0
      ? layered
      : finishedAd
        ? [soleFinishedImage]
        : layered.length > 0
          ? layered
          : [
              {
                id: 'img-gpt-image',
                type: 'IMAGE',
                assetId: input.localAssetId,
                x: 0,
                y: 0,
                width,
                height,
                zIndex: 0,
              },
            ];

  const headlineFromLayers =
    editableFinishedAd
      ? (() => {
          const h = elements.find(
            (el) => el.type === 'TEXT' && (el.id === 'headline' || el.role === 'headline'),
          );
          return h && h.type === 'TEXT' ? h.content : '';
        })()
      : '';

  return {
    id: mintCreatePostId() || `p-gpt-image-${Date.now()}-${input.index}`,
    platform: 'instagram',
    format: preset === 'story' ? 'story' : preset === 'reelsCover' ? 'reel' : preset === 'carousel' ? 'carousel' : 'feed',
    formatPreset: preset,
    width,
    height,
    status: 'draft',
    thumbUrl: '',
    name: editableFinishedAd ? 'Editable Finished Ad' : finishedAd ? 'Finished Ad' : 'GPT Image',
    headline: finishedAd && !editableFinishedAd ? '' : headlineFromLayers || input.headline || '',
    description: '',
    caption: '',
    coverAssetId: coverId,
    linkedProjectId: input.linkedProjectId,
    elements,
    generationMeta: {
      provider: input.provider || 'gpt-image',
      model: input.model,
      generated_by: finishedAd ? 'creative_director_generate_ad' : 'gpt_image_design',
      project_id: input.linkedProjectId,
      user_prompt: input.instruction,
      campaign_context_id: input.campaignContextId,
      generation_context_id: input.sessionId,
      selected_asset_ids: [input.localAssetId],
      ...(finishedAd
        ? {
            production_mode: editableFinishedAd ? 'editable_finished_ad' : 'finished_ad',
            logo_asset_id: input.logoAssetId ?? null,
            interior_asset_id: input.interiorAssetId ?? null,
            master_background_asset_id: masterBg,
            finished_ad_raster_asset_id:
              input.finishedAdRasterAssetId ?? (editableFinishedAd ? input.localAssetId : null),
            design_spec: input.designSpec ?? null,
          }
        : {}),
      gpt_image: {
        local_asset_id: input.localAssetId,
        composition_base_asset_id: editableFinishedAd
          ? masterBg
          : finishedAd
            ? null
            : input.compositionBaseAssetId ?? null,
        source_asset_id: input.sourceAssetId,
        session_id: input.sessionId,
        composition_warnings: input.compositionWarnings ?? [],
        editable_layers: editableFinishedAd ? true : finishedAd ? false : layered.length > 0,
      },
    },
    campaignContextId: input.campaignContextId,
    generationContextId: input.sessionId,
    generationLifecycle: 'ready',
    createdAt: new Date().toISOString(),
  };
}

export function isMediaAssetId(value: string | null | undefined): value is string {
  return Boolean(value && isMediaAssetUuid(value));
}
