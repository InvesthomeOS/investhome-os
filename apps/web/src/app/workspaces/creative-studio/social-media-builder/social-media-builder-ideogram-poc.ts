/**
 * Ideogram External Design AI POC helpers — isolated from Native SMB generation.
 * Flattened images only; no Ideogram text → canvas schema conversion.
 */

import { getCreativeStudioMediaContentUrl } from '@/lib/api/creative-studio';

import { mintCreatePostId, type SocialPost } from './social-media-builder-model';
import { isMediaAssetUuid } from '../_components/cs-image-ref';

export type DesignEngineKind = 'native' | 'ideogram' | 'gpt-image';

export type IdeogramPocVariant = 'A' | 'B' | 'C';

export type IdeogramPocOutput = {
  variant: IdeogramPocVariant;
  artDirection: string;
  localAssetId: string;
  localAssetUrl: string;
  providerGenerationId: string | null;
  originalRemoteUrl: string | null;
  metadata: Record<string, unknown>;
};

export type IdeogramPocSession = {
  sessionId: string;
  instruction: string;
  createdAt: string;
  linkedProjectId: string;
  campaignContextId: string | null;
  sourceAssetId: string;
  sourceFilename: string;
  providerCallCount: number;
  model: string;
  endpoint: string;
  brief: Record<string, unknown>;
  outputs: IdeogramPocOutput[];
};

export const IDEOGRAM_POC_STAGES = [
  'ideogramBrief',
  'ideogramSource',
  'ideogramGenerating',
  'ideogramSaving',
] as const;

export function parseIdeogramPocSession(raw: unknown): IdeogramPocSession | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw as Record<string, unknown>;
  const sessionId = typeof body.sessionId === 'string' ? body.sessionId : typeof body.session_id === 'string' ? body.session_id : '';
  const linkedProjectId =
    typeof body.linkedProjectId === 'string'
      ? body.linkedProjectId
      : typeof body.linked_project_id === 'string'
        ? body.linked_project_id
        : '';
  const outputsRaw = Array.isArray(body.outputs) ? body.outputs : [];
  const outputs: IdeogramPocOutput[] = [];
  for (const row of outputsRaw) {
    if (!row || typeof row !== 'object') continue;
    const item = row as Record<string, unknown>;
    const variant = item.variant === 'A' || item.variant === 'B' || item.variant === 'C' ? item.variant : null;
    const localAssetId =
      typeof item.localAssetId === 'string'
        ? item.localAssetId
        : typeof item.local_asset_id === 'string'
          ? item.local_asset_id
          : '';
    if (!variant || !isMediaAssetUuid(localAssetId)) continue;
    outputs.push({
      variant,
      artDirection: String(item.artDirection ?? item.art_direction ?? ''),
      localAssetId,
      localAssetUrl: String(item.localAssetUrl ?? item.local_asset_url ?? ''),
      providerGenerationId:
        typeof item.providerGenerationId === 'string'
          ? item.providerGenerationId
          : typeof item.provider_generation_id === 'string'
            ? item.provider_generation_id
            : null,
      originalRemoteUrl:
        typeof item.originalRemoteUrl === 'string'
          ? item.originalRemoteUrl
          : typeof item.original_remote_url === 'string'
            ? item.original_remote_url
            : null,
      metadata: item.metadata && typeof item.metadata === 'object' && !Array.isArray(item.metadata)
        ? (item.metadata as Record<string, unknown>)
        : {},
    });
  }
  if (!sessionId || !linkedProjectId || !outputs.length) return null;
  return {
    sessionId,
    instruction: typeof body.instruction === 'string' ? body.instruction : '',
    createdAt: typeof body.createdAt === 'string' ? body.createdAt : typeof body.created_at === 'string' ? body.created_at : '',
    linkedProjectId,
    campaignContextId:
      typeof body.campaignContextId === 'string'
        ? body.campaignContextId
        : typeof body.campaign_context_id === 'string'
          ? body.campaign_context_id
          : null,
    sourceAssetId: String(body.sourceAssetId ?? body.source_asset_id ?? ''),
    sourceFilename: String(body.sourceFilename ?? body.source_filename ?? ''),
    providerCallCount: Number(body.providerCallCount ?? body.provider_call_count ?? 0) || 0,
    model: String(body.model ?? ''),
    endpoint: String(body.endpoint ?? ''),
    brief: body.brief && typeof body.brief === 'object' && !Array.isArray(body.brief)
      ? (body.brief as Record<string, unknown>)
      : {},
    outputs,
  };
}

export function serializeIdeogramPocSession(
  session: IdeogramPocSession | null,
): Record<string, unknown> | null {
  if (!session) return null;
  return {
    sessionId: session.sessionId,
    instruction: session.instruction,
    createdAt: session.createdAt,
    linkedProjectId: session.linkedProjectId,
    campaignContextId: session.campaignContextId,
    sourceAssetId: session.sourceAssetId,
    sourceFilename: session.sourceFilename,
    providerCallCount: session.providerCallCount,
    model: session.model,
    endpoint: session.endpoint,
    brief: session.brief,
    outputs: session.outputs.map((item) => ({
      variant: item.variant,
      artDirection: item.artDirection,
      localAssetId: item.localAssetId,
      localAssetUrl: item.localAssetUrl,
      providerGenerationId: item.providerGenerationId,
      originalRemoteUrl: item.originalRemoteUrl,
      metadata: item.metadata,
    })),
  };
}

export function ideogramOutputPreviewUrl(
  output: IdeogramPocOutput,
  linkedProjectId: string | null,
): string {
  if (output.localAssetUrl.startsWith('http') || output.localAssetUrl.startsWith('/')) {
    if (linkedProjectId && output.localAssetUrl.includes('/creative-studio/media/assets/')) {
      return getCreativeStudioMediaContentUrl(output.localAssetId, {
        linked_project_id: linkedProjectId,
      });
    }
    return output.localAssetUrl;
  }
  return getCreativeStudioMediaContentUrl(output.localAssetId, {
    linked_project_id: linkedProjectId,
  });
}

/** Flattened Ideogram creative as a NEW SMB post. Does not rewrite the source project image. */
export function createFlattenedIdeogramPost(input: {
  output: IdeogramPocOutput;
  session: IdeogramPocSession;
  linkedProjectId: string;
  index: number;
}): SocialPost {
  const { output, session, linkedProjectId, index } = input;
  const size = 1080;
  const headline =
    typeof session.brief?.visible_copy === 'object' && session.brief.visible_copy
      ? String((session.brief.visible_copy as Record<string, unknown>).headline || '')
      : '';
  return {
    id: mintCreatePostId() || `p-ideogram-${Date.now()}-${index}`,
    platform: 'instagram',
    format: 'feed',
    formatPreset: 'square',
    width: size,
    height: size,
    status: 'draft',
    thumbUrl: '',
    name: `Ideogram ${output.variant}`,
    headline,
    description: output.artDirection,
    caption: '',
    coverAssetId: output.localAssetId,
    linkedProjectId,
    elements: [
      {
        id: `img-ideogram-${output.variant.toLowerCase()}`,
        type: 'IMAGE',
        assetId: output.localAssetId,
        x: 0,
        y: 0,
        width: size,
        height: size,
        zIndex: 0,
      },
    ],
    generationMeta: {
      provider: 'ideogram',
      model: session.model,
      generated_by: 'ideogram_design_poc',
      project_id: linkedProjectId,
      user_prompt: session.instruction,
      campaign_context_id: session.campaignContextId,
      generation_context_id: session.sessionId,
      selected_asset_ids: [output.localAssetId],
      ideogram: {
        variant: output.variant,
        art_direction: output.artDirection,
        provider_generation_id: output.providerGenerationId,
        original_remote_url: output.originalRemoteUrl,
        local_asset_id: output.localAssetId,
        source_asset_id: session.sourceAssetId,
        session_id: session.sessionId,
      },
      ...output.metadata,
    },
    campaignContextId: session.campaignContextId,
    generationContextId: session.sessionId,
    generationLifecycle: 'ready',
    createdAt: new Date().toISOString(),
  };
}

export function sessionFromIdeogramResponse(
  response: {
    session_id: string;
    linked_project_id: string;
    campaign_context_id: string | null;
    model: string;
    endpoint: string;
    brief: Record<string, unknown>;
    provider_call_count: number;
    source_image: { asset_id: string; filename: string };
    outputs: Array<{
      variant: IdeogramPocVariant;
      art_direction: string;
      local_asset_id: string;
      local_asset_url: string;
      provider_generation_id: string | null;
      original_remote_url: string | null;
      metadata: Record<string, unknown>;
    }>;
  },
  instruction: string,
  previous?: IdeogramPocSession | null,
): IdeogramPocSession {
  const incoming: IdeogramPocOutput[] = response.outputs.map((item) => ({
    variant: item.variant,
    artDirection: item.art_direction,
    localAssetId: item.local_asset_id,
    localAssetUrl: item.local_asset_url,
    providerGenerationId: item.provider_generation_id,
    originalRemoteUrl: item.original_remote_url,
    metadata: item.metadata ?? {},
  }));
  return {
    sessionId: response.session_id,
    instruction,
    createdAt: previous?.createdAt || new Date().toISOString(),
    linkedProjectId: response.linked_project_id,
    campaignContextId: response.campaign_context_id,
    sourceAssetId: response.source_image.asset_id,
    sourceFilename: response.source_image.filename,
    providerCallCount: (previous?.providerCallCount ?? 0) + (response.provider_call_count || 0),
    model: response.model,
    endpoint: response.endpoint,
    brief: response.brief,
    outputs: mergeIdeogramOutputs(previous?.outputs ?? [], incoming),
  };
}

export function mergeIdeogramOutputs(
  existing: IdeogramPocOutput[],
  incoming: IdeogramPocOutput[],
): IdeogramPocOutput[] {
  const byVariant = new Map<IdeogramPocVariant, IdeogramPocOutput>();
  for (const row of existing) byVariant.set(row.variant, row);
  for (const row of incoming) byVariant.set(row.variant, row);
  return (['A', 'B', 'C'] as const).map((v) => byVariant.get(v)).filter((row): row is IdeogramPocOutput => Boolean(row));
}
