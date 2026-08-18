/**
 * GPT Image SMB helpers — flattened raster posts. Native/Ideogram stay intact.
 */

import { getCreativeStudioMediaContentUrl } from '@/lib/api/creative-studio';

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

/** Flattened GPT Image creative as a NEW SMB post. Architecture lives in the raster. */
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
}): SocialPost {
  const preset = input.formatPreset;
  const size = resolveFormatSize(preset);
  const width = input.canvasWidth && input.canvasWidth > 0 ? input.canvasWidth : size.w;
  const height = input.canvasHeight && input.canvasHeight > 0 ? input.canvasHeight : size.h;
  return {
    id: mintCreatePostId() || `p-gpt-image-${Date.now()}-${input.index}`,
    platform: 'instagram',
    format: preset === 'story' ? 'story' : preset === 'reelsCover' ? 'reel' : preset === 'carousel' ? 'carousel' : 'feed',
    formatPreset: preset,
    width,
    height,
    status: 'draft',
    thumbUrl: '',
    name: 'GPT Image',
    headline: input.headline || '',
    description: '',
    caption: '',
    coverAssetId: input.localAssetId,
    linkedProjectId: input.linkedProjectId,
    elements: [
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
    ],
    generationMeta: {
      provider: 'gpt-image',
      model: input.model,
      generated_by: 'gpt_image_design',
      project_id: input.linkedProjectId,
      user_prompt: input.instruction,
      campaign_context_id: input.campaignContextId,
      generation_context_id: input.sessionId,
      selected_asset_ids: [input.localAssetId],
      gpt_image: {
        local_asset_id: input.localAssetId,
        source_asset_id: input.sourceAssetId,
        session_id: input.sessionId,
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
