/**
 * Social Media Builder AI Design Engine client helpers (Phase 1).
 * NL create/edit → server Design Ops → same posts[]/elements[] canvas.
 */

import type {
  SocialDesignGenerationMeta,
  SocialDesignMode,
  SocialDesignRequest,
  SocialDesignResponse,
} from '@/lib/api/creative-studio';

import { isMediaAssetUuid, type CsImageRef } from '../_components/cs-image-ref';

import {
  collectSelectedAssetIds,
  type SocialGenerationMeta,
} from './social-media-builder-generation';
import { parseSocialPost, serializeSocialPost } from './social-media-builder-persistence';
import type { PlatformKey, SocialPost } from './social-media-builder-model';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const GENERATION_VERBS = [
  'hazırla',
  'hazirla',
  'oluştur',
  'olustur',
  'create a',
  'create an',
  'generate a',
  'prepare a',
  'postu hazırla',
  'post hazırla',
  'instagram post',
  'kare post',
  'complete post',
  'yeni post',
  'new post',
];

const COMPLETE_POST_MARKERS = ['post', 'instagram', 'kare', 'feed', 'gönderi', 'gonderi', 'creative'];

const SURGICAL_EDIT_HINTS = [
  'taşı',
  'tasi',
  'yukarı al',
  'yukari al',
  'aşağı al',
  'asagi al',
  'sola al',
  'sağa al',
  'saga al',
  'kaldır',
  'kaldir',
  'küçült',
  'kucult',
  'büyüt',
  'rengini',
  'başlığı biraz',
  'basligi biraz',
  'cta\'yı kaldır',
  'cta\'yi kaldir',
  'move the',
  'remove the',
  'delete the',
  'başka bir',
  'baska bir',
  'another photo',
  'another image',
];

function isCompletePostGeneration(instruction: string): boolean {
  const instr = (instruction || '').toLowerCase();
  const hasVerb = GENERATION_VERBS.some((v) => instr.includes(v));
  const hasPost = COMPLETE_POST_MARKERS.some((m) => instr.includes(m));
  return hasVerb && hasPost;
}

function isSurgicalEdit(instruction: string): boolean {
  const instr = (instruction || '').toLowerCase();
  return SURGICAL_EDIT_HINTS.some((h) => instr.includes(h));
}

export function inferDesignMode(
  instruction: string,
  posts: SocialPost[],
  preferred?: SocialDesignMode | null,
): SocialDesignMode {
  if (!posts.length) return 'create';
  const generation = isCompletePostGeneration(instruction);
  const surgical = isSurgicalEdit(instruction);
  if (generation && !surgical) return 'create';
  if (surgical && !generation) return 'edit';
  if (generation && surgical) return 'create';
  if (preferred === 'edit') return 'edit';
  if (preferred === 'create') return 'create';
  return 'create';
}

export type DesignGenerationMeta = SocialGenerationMeta & {
  brand_context_status?: string;
  mode?: SocialDesignMode;
  planner?: string;
  ops_count?: number;
  generated_by?: string | null;
  project_id?: string | null;
  user_prompt?: string | null;
  generation_intent?: Record<string, unknown> | null;
  source_document_ids?: string[];
  selected_asset_ids?: string[];
  generated_at?: string | null;
  content_package?: Record<string, unknown> | null;
  design_plan?: Record<string, unknown> | null;
  campaign_facts?: Record<string, unknown>[];
};

export type BuildSocialDesignResult =
  | { ok: true; request: SocialDesignRequest }
  | { ok: false; reason: 'missing_project' | 'missing_instruction' };

export type SelectedElementDesignContext = {
  id: string;
  type: string;
  role?: string | null;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex?: number;
  content?: string | null;
  label?: string | null;
  fontSize?: number | null;
  fontWeight?: string | null;
  align?: string | null;
  color?: string | null;
  backgroundColor?: string | null;
  textColor?: string | null;
  assetId?: string | null;
};

/** Snapshot a canvas element for AI Design builder_context (no media URLs). */
export function selectedElementToDesignContext(
  el: {
    id: string;
    type: string;
    x: number;
    y: number;
    width: number;
    height: number;
    zIndex?: number;
    role?: string;
    content?: string;
    label?: string;
    fontSize?: number;
    fontWeight?: string;
    align?: string;
    color?: string;
    backgroundColor?: string;
    textColor?: string;
    assetId?: string | null;
  } | null | undefined,
): SelectedElementDesignContext | null {
  if (!el || typeof el.id !== 'string' || !el.id) return null;
  const base: SelectedElementDesignContext = {
    id: el.id,
    type: el.type,
    x: Number.isFinite(el.x) ? el.x : 0,
    y: Number.isFinite(el.y) ? el.y : 0,
    width: Math.max(8, Number.isFinite(el.width) ? el.width : 100),
    height: Math.max(8, Number.isFinite(el.height) ? el.height : 40),
    zIndex: Number.isFinite(el.zIndex) ? el.zIndex : 1,
  };
  if (el.type === 'TEXT') {
    return {
      ...base,
      role: el.role ?? 'custom',
      content: el.content ?? '',
      fontSize: el.fontSize ?? null,
      fontWeight: el.fontWeight ?? null,
      align: el.align ?? null,
      color: el.color ?? null,
    };
  }
  if (el.type === 'BUTTON') {
    return {
      ...base,
      role: 'cta',
      label: el.label ?? '',
      backgroundColor: el.backgroundColor ?? null,
      textColor: el.textColor ?? null,
    };
  }
  if (el.type === 'IMAGE') {
    return {
      ...base,
      role: 'image',
      assetId: el.assetId ?? null,
    };
  }
  return base;
}

export function buildSocialDesignRequest(input: {
  linkedProjectId: string | null | undefined;
  instruction: string;
  posts: SocialPost[];
  selectedPostId: string | null;
  selectedElement?: SelectedElementDesignContext | null;
  coverImage?: CsImageRef | null;
  galleryImages?: CsImageRef[] | null;
  language?: string | null;
  platforms?: Iterable<PlatformKey | string>;
  mode?: SocialDesignMode | null;
}): BuildSocialDesignResult {
  const linked = typeof input.linkedProjectId === 'string' ? input.linkedProjectId.trim() : '';
  if (!linked || !UUID_RE.test(linked)) {
    return { ok: false, reason: 'missing_project' };
  }
  const instruction = (input.instruction || '').trim();
  if (!instruction) {
    return { ok: false, reason: 'missing_instruction' };
  }

  const selected_asset_ids = collectSelectedAssetIds(input.coverImage, input.galleryImages).filter(
    (id) => UUID_RE.test(id) && !/^https?:/i.test(id),
  );
  // Also include per-post cover + image element asset ids (project-scoped UUIDs only)
  for (const post of input.posts) {
    if (post.coverAssetId && isMediaAssetUuid(post.coverAssetId) && !selected_asset_ids.includes(post.coverAssetId)) {
      selected_asset_ids.push(post.coverAssetId);
    }
    for (const el of post.elements) {
      if (el.type === 'IMAGE' && el.assetId && isMediaAssetUuid(el.assetId) && !selected_asset_ids.includes(el.assetId)) {
        selected_asset_ids.push(el.assetId);
      }
    }
  }

  const platforms = input.platforms
    ? Array.from(input.platforms).map(String).filter(Boolean)
    : [];
  const mode = inferDesignMode(instruction, input.posts, input.mode);
  const selectedElement =
    input.selectedElement && typeof input.selectedElement.id === 'string'
      ? input.selectedElement
      : null;

  return {
    ok: true,
    request: {
      linked_project_id: linked,
      instruction,
      mode,
      draft: {
        posts: input.posts.map(serializeSocialPost),
        selected_post_id: input.selectedPostId,
      },
      selected_asset_ids,
      language: input.language?.trim() || null,
      builder_context: {
        builder: 'social',
        design_engine: 'phase1',
        platforms,
        ...(selectedElement
          ? {
              selectedElementId: selectedElement.id,
              selected_element_id: selectedElement.id,
              selected_element: selectedElement,
            }
          : {}),
      },
    },
  };
}

export function applyDesignResponseToPosts(
  response: SocialDesignResponse,
  fallbackLinkedProjectId: string | null,
): { posts: SocialPost[]; selectedPostId: string | null } {
  const posts = (response.posts ?? [])
    .map((raw) => parseSocialPost(raw, fallbackLinkedProjectId))
    .filter((p): p is SocialPost => p != null);

  let selectedPostId =
    typeof response.selected_post_id === 'string' && response.selected_post_id.trim()
      ? response.selected_post_id.trim()
      : null;
  if (selectedPostId && !posts.some((p) => p.id === selectedPostId)) {
    selectedPostId = posts[0]?.id ?? null;
  }
  if (!selectedPostId && posts.length) selectedPostId = posts[0]!.id;

  return { posts, selectedPostId };
}

export function toDesignGenerationMeta(response: SocialDesignResponse): DesignGenerationMeta {
  const meta = response.meta;
  return {
    citations: meta?.citations ?? [],
    warnings: meta?.warnings ?? [],
    grounded: Boolean(meta?.grounded),
    retrieval_confidence: meta?.retrieval_confidence ?? 0,
    asset_ids_used: meta?.asset_ids_used ?? [],
    provider: meta?.provider ?? '',
    model: meta?.model ?? '',
    brand_context_status: meta?.brand_context_status,
    mode: meta?.mode ?? response.mode,
    planner: meta?.planner,
    ops_count: response.ops?.length ?? 0,
    generated_by: meta?.generated_by ?? null,
    project_id: meta?.project_id ?? null,
    user_prompt: meta?.user_prompt ?? null,
    generation_intent: meta?.generation_intent ?? null,
    source_document_ids: meta?.source_document_ids ?? [],
    selected_asset_ids: meta?.selected_asset_ids ?? meta?.asset_ids_used ?? [],
    generated_at: meta?.generated_at ?? null,
    content_package: meta?.content_package ?? null,
    design_plan: meta?.design_plan ?? null,
    campaign_facts: meta?.campaign_facts ?? [],
  };
}

export function serializeGenerationMetaForDraft(
  meta: DesignGenerationMeta | null,
): Record<string, unknown> | null {
  if (!meta) return null;
  return {
    citations: meta.citations,
    warnings: meta.warnings,
    grounded: meta.grounded,
    retrieval_confidence: meta.retrieval_confidence,
    asset_ids_used: meta.asset_ids_used,
    provider: meta.provider,
    model: meta.model,
    brand_context_status: meta.brand_context_status ?? null,
    mode: meta.mode ?? null,
    planner: meta.planner ?? null,
    ops_count: meta.ops_count ?? null,
    generated_by: meta.generated_by ?? null,
    project_id: meta.project_id ?? null,
    user_prompt: meta.user_prompt ?? null,
    generation_intent: meta.generation_intent ?? null,
    source_document_ids: meta.source_document_ids ?? [],
    selected_asset_ids: meta.selected_asset_ids ?? [],
    generated_at: meta.generated_at ?? null,
    content_package: meta.content_package ?? null,
    design_plan: meta.design_plan ?? null,
    campaign_facts: meta.campaign_facts ?? [],
  };
}

export function parseGenerationMetaFromDraft(
  raw: Record<string, unknown> | null | undefined,
): DesignGenerationMeta | null {
  if (!raw || typeof raw !== 'object') return null;
  const provider = typeof raw.provider === 'string' ? raw.provider : '';
  const model = typeof raw.model === 'string' ? raw.model : '';
  return {
    citations: Array.isArray(raw.citations) ? (raw.citations as DesignGenerationMeta['citations']) : [],
    warnings: Array.isArray(raw.warnings) ? raw.warnings.filter((w): w is string => typeof w === 'string') : [],
    grounded: Boolean(raw.grounded),
    retrieval_confidence: typeof raw.retrieval_confidence === 'number' ? raw.retrieval_confidence : 0,
    asset_ids_used: Array.isArray(raw.asset_ids_used)
      ? raw.asset_ids_used.filter((id): id is string => typeof id === 'string')
      : [],
    provider,
    model,
    brand_context_status: typeof raw.brand_context_status === 'string' ? raw.brand_context_status : undefined,
    mode: raw.mode === 'edit' || raw.mode === 'create' ? raw.mode : undefined,
    planner: typeof raw.planner === 'string' ? raw.planner : undefined,
    ops_count: typeof raw.ops_count === 'number' ? raw.ops_count : undefined,
    generated_by: typeof raw.generated_by === 'string' ? raw.generated_by : null,
    project_id: typeof raw.project_id === 'string' ? raw.project_id : null,
    user_prompt: typeof raw.user_prompt === 'string' ? raw.user_prompt : null,
    generation_intent:
      raw.generation_intent && typeof raw.generation_intent === 'object' && !Array.isArray(raw.generation_intent)
        ? (raw.generation_intent as Record<string, unknown>)
        : null,
    source_document_ids: Array.isArray(raw.source_document_ids)
      ? raw.source_document_ids.filter((id): id is string => typeof id === 'string')
      : [],
    selected_asset_ids: Array.isArray(raw.selected_asset_ids)
      ? raw.selected_asset_ids.filter((id): id is string => typeof id === 'string')
      : [],
    generated_at: typeof raw.generated_at === 'string' ? raw.generated_at : null,
    content_package:
      raw.content_package && typeof raw.content_package === 'object' && !Array.isArray(raw.content_package)
        ? (raw.content_package as Record<string, unknown>)
        : null,
    design_plan:
      raw.design_plan && typeof raw.design_plan === 'object' && !Array.isArray(raw.design_plan)
        ? (raw.design_plan as Record<string, unknown>)
        : null,
    campaign_facts: Array.isArray(raw.campaign_facts)
      ? raw.campaign_facts.filter((f): f is Record<string, unknown> => !!f && typeof f === 'object')
      : [],
  };
}

export function hasDesignInsufficientContext(
  response: Pick<SocialDesignResponse, 'meta'>,
): boolean {
  if (response.meta?.grounded === false) return true;
  const warnings = response.meta?.warnings ?? [];
  return warnings.some(
    (w) =>
      w === 'insufficient_context' ||
      w === 'insufficient_retrieved_content' ||
      w.includes('insufficient'),
  );
}

export type { SocialDesignGenerationMeta, SocialDesignMode, SocialDesignResponse };
