/**
 * Investhome Art Director session — editable A/B/C DesignPlans on real assets.
 * Isolated from Ideogram flattened POC. Never stores remote generated URLs.
 */

import type { SocialDesignResponse } from '@/lib/api/creative-studio';

import { parseSocialPost, serializeSocialPost } from './social-media-builder-persistence';
import type { SocialPost } from './social-media-builder-model';

export type ArtDirectorVariantKey = 'A' | 'B' | 'C';

export type ArtDirectorProvenance = {
  projectId: string;
  selectedAssetId: string | null;
  source: string | null;
  filename: string | null;
  category: string | null;
  visualSubject: string | null;
  financialFactsSource: string | null;
  logoAssetId: string | null;
  logoStatus: string | null;
};

export type ArtDirectorVariant = {
  key: ArtDirectorVariantKey;
  label: string;
  creativeDirection: string;
  composition: string;
  campaignType: string;
  designPlan: Record<string, unknown>;
  post: SocialPost | null;
  provenance: ArtDirectorProvenance | null;
};

export type ArtDirectorSession = {
  instruction: string;
  createdAt: string;
  linkedProjectId: string;
  selectedVariant: ArtDirectorVariantKey;
  campaignType: string;
  provenance: ArtDirectorProvenance | null;
  selectedAsset: {
    assetId: string;
    filename: string;
    category: string | null;
    visualSubject: string | null;
    source: string | null;
  } | null;
  variants: ArtDirectorVariant[];
};

function asRecord(raw: unknown): Record<string, unknown> | null {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

function parseProvenance(raw: unknown): ArtDirectorProvenance | null {
  const body = asRecord(raw);
  if (!body) return null;
  const projectId = String(body.projectId ?? body.project_id ?? '');
  if (!projectId) return null;
  return {
    projectId,
    selectedAssetId:
      typeof body.selectedAssetId === 'string'
        ? body.selectedAssetId
        : typeof body.selected_asset_id === 'string'
          ? body.selected_asset_id
          : null,
    source: typeof body.source === 'string' ? body.source : null,
    filename: typeof body.filename === 'string' ? body.filename : null,
    category: typeof body.category === 'string' ? body.category : null,
    visualSubject:
      typeof body.visualSubject === 'string'
        ? body.visualSubject
        : typeof body.visual_subject === 'string'
          ? body.visual_subject
          : null,
    financialFactsSource:
      typeof body.financialFactsSource === 'string'
        ? body.financialFactsSource
        : typeof body.financial_facts_source === 'string'
          ? body.financial_facts_source
          : null,
    logoAssetId:
      typeof body.logoAssetId === 'string'
        ? body.logoAssetId
        : typeof body.logo_asset_id === 'string'
          ? body.logo_asset_id
          : null,
    logoStatus:
      typeof body.logoStatus === 'string'
        ? body.logoStatus
        : typeof body.logo_status === 'string'
          ? body.logo_status
          : null,
  };
}

function parseVariant(raw: unknown, linkedProjectId: string | null): ArtDirectorVariant | null {
  const body = asRecord(raw);
  if (!body) return null;
  const key = body.key === 'A' || body.key === 'B' || body.key === 'C' ? body.key : null;
  if (!key) return null;
  const postRaw = asRecord(body.post);
  return {
    key,
    label: String(body.label ?? ''),
    creativeDirection: String(body.creativeDirection ?? body.creative_direction ?? ''),
    composition: String(body.composition ?? ''),
    campaignType: String(body.campaignType ?? body.campaign_type ?? ''),
    designPlan: asRecord(body.designPlan) ?? asRecord(body.design_plan) ?? {},
    post: postRaw ? parseSocialPost(postRaw, linkedProjectId) : null,
    provenance: parseProvenance(body.provenance),
  };
}

export function parseArtDirectorSession(
  raw: unknown,
  linkedProjectId?: string | null,
): ArtDirectorSession | null {
  const body = asRecord(raw);
  if (!body) return null;
  const variantsRaw = Array.isArray(body.variants) ? body.variants : [];
  const projectId =
    typeof body.linkedProjectId === 'string'
      ? body.linkedProjectId
      : typeof body.linked_project_id === 'string'
        ? body.linked_project_id
        : linkedProjectId || '';
  const variants = variantsRaw
    .map((row) => parseVariant(row, projectId))
    .filter((row): row is ArtDirectorVariant => row != null);
  if (!variants.length) return null;
  const selectedAssetRaw = asRecord(body.selectedAsset) ?? asRecord(body.selected_asset);
  return {
    instruction: typeof body.instruction === 'string' ? body.instruction : '',
    createdAt: typeof body.createdAt === 'string' ? body.createdAt : typeof body.created_at === 'string' ? body.created_at : '',
    linkedProjectId: projectId,
    selectedVariant:
      body.selectedVariant === 'B' || body.selectedVariant === 'C' || body.selected_variant === 'B' || body.selected_variant === 'C'
        ? ((body.selectedVariant || body.selected_variant) as ArtDirectorVariantKey)
        : 'A',
    campaignType: String(body.campaignType ?? body.campaign_type ?? ''),
    provenance: parseProvenance(body.provenance),
    selectedAsset: selectedAssetRaw
      ? {
          assetId: String(selectedAssetRaw.assetId ?? selectedAssetRaw.asset_id ?? ''),
          filename: String(selectedAssetRaw.filename ?? ''),
          category:
            typeof selectedAssetRaw.category === 'string' ? selectedAssetRaw.category : null,
          visualSubject:
            typeof selectedAssetRaw.visualSubject === 'string'
              ? selectedAssetRaw.visualSubject
              : typeof selectedAssetRaw.visual_subject === 'string'
                ? selectedAssetRaw.visual_subject
                : null,
          source: typeof selectedAssetRaw.source === 'string' ? selectedAssetRaw.source : null,
        }
      : null,
    variants,
  };
}

export function serializeArtDirectorSession(
  session: ArtDirectorSession | null,
): Record<string, unknown> | null {
  if (!session) return null;
  return {
    instruction: session.instruction,
    createdAt: session.createdAt,
    linkedProjectId: session.linkedProjectId,
    selectedVariant: session.selectedVariant,
    campaignType: session.campaignType,
    provenance: session.provenance,
    selectedAsset: session.selectedAsset,
    variants: session.variants.map((variant) => ({
      key: variant.key,
      label: variant.label,
      creativeDirection: variant.creativeDirection,
      composition: variant.composition,
      campaignType: variant.campaignType,
      designPlan: variant.designPlan,
      post: variant.post ? serializeSocialPost(variant.post) : null,
      provenance: variant.provenance,
    })),
  };
}

export function sessionFromDesignResponse(
  response: SocialDesignResponse,
  instruction: string,
): ArtDirectorSession | null {
  const variantsRaw = Array.isArray(response.design_variants) ? response.design_variants : [];
  if (!variantsRaw.length) return null;
  return parseArtDirectorSession(
    {
      instruction,
      createdAt: new Date().toISOString(),
      linkedProjectId: response.linked_project_id,
      selectedVariant: response.selected_variant ?? 'A',
      campaignType: response.meta?.art_director?.campaign_type ?? variantsRaw[0]?.campaign_type,
      provenance: response.provenance ?? response.meta?.provenance,
      selectedAsset: response.selected_asset ?? response.meta?.selected_asset,
      variants: variantsRaw,
    },
    response.linked_project_id,
  );
}

function parseSelectedAssetFromResponse(
  raw: unknown,
): ArtDirectorSession['selectedAsset'] {
  const body = asRecord(raw);
  if (!body) return null;
  const assetId = String(body.assetId ?? body.asset_id ?? '');
  if (!assetId) return null;
  return {
    assetId,
    filename: String(body.filename ?? ''),
    category: typeof body.category === 'string' ? body.category : null,
    visualSubject:
      typeof body.visualSubject === 'string'
        ? body.visualSubject
        : typeof body.visual_subject === 'string'
          ? body.visual_subject
          : null,
    source: typeof body.source === 'string' ? body.source : null,
  };
}

export function applyRealAssetToSession(
  session: ArtDirectorSession,
  asset: NonNullable<ArtDirectorSession['selectedAsset']>,
): ArtDirectorSession {
  const patchPost = (post: SocialPost | null): SocialPost | null => {
    if (!post) return post;
    return {
      ...post,
      coverAssetId: asset.assetId,
      elements: post.elements.map((el) =>
        el.type === 'IMAGE' && (el.role === 'background' || el.role === 'cover' || el.role === 'image')
          ? { ...el, assetId: asset.assetId }
          : el,
      ),
    };
  };
  const patchProvenance = (prov: ArtDirectorProvenance | null): ArtDirectorProvenance | null => {
    if (!prov) return prov;
    return {
      ...prov,
      selectedAssetId: asset.assetId,
      filename: asset.filename,
      category: asset.category,
      visualSubject: asset.visualSubject,
      source: asset.source,
    };
  };
  return {
    ...session,
    selectedAsset: asset,
    provenance: patchProvenance(session.provenance),
    variants: session.variants.map((variant) => ({
      ...variant,
      post: patchPost(variant.post),
      provenance: patchProvenance(variant.provenance),
    })),
  };
}

export function mergeArtDirectorSessionFromResponse(
  current: ArtDirectorSession | null,
  response: SocialDesignResponse,
  instruction: string,
): ArtDirectorSession | null {
  const created = sessionFromDesignResponse(response, instruction);
  if (created) return created;
  if (!current) return null;
  const nextAsset = parseSelectedAssetFromResponse(
    response.selected_asset ?? response.meta?.selected_asset,
  );
  if (!nextAsset) return current;
  return applyRealAssetToSession(current, nextAsset);
}

export function applyArtDirectorVariantToPosts(
  posts: SocialPost[],
  selectedPostId: string | null,
  variant: ArtDirectorVariant,
): SocialPost[] {
  const nextPost = variant.post;
  if (!nextPost) return posts;
  const targetId = selectedPostId || nextPost.id;
  return posts.map((post) => {
    if (post.id !== targetId) return post;
    return {
      ...nextPost,
      id: post.id,
      linkedProjectId: post.linkedProjectId || nextPost.linkedProjectId,
      createdAt: post.createdAt || nextPost.createdAt,
      updatedAt: new Date().toISOString(),
    };
  });
}
