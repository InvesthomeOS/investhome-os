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
  'another temple photo',
  'more minimal',
  'more premium',
  'show more photo',
  'left-align',
  'remove cta',
  'başlığı daha güçlü',
  'basligi daha guclu',
  'adres bilgisini',
  'daha kurumsal',
  'make headline stronger',
  'remove the address',
  'rakamları alt alta',
  'rakamlari alt alta',
  'rakamları kart',
  'rakamlari kart',
  'getiriyi öne',
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
  options?: { explicit?: boolean },
): SocialDesignMode {
  if (!posts.length) return 'create';
  if (options?.explicit && (preferred === 'create' || preferred === 'edit')) {
    return preferred;
  }
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
  structured_metrics?: Record<string, unknown>[];
  metric_group?: Record<string, unknown> | null;
  creative_concept?: Record<string, unknown> | null;
  creative_plan?: Record<string, unknown> | null;
  design_quality?: Record<string, unknown> | null;
  validation?: Record<string, unknown> | null;
  marketing_strategy?: Record<string, unknown> | null;
  copy_quality?: Record<string, unknown> | null;
  headline_candidates?: Record<string, unknown>[];
  campaign_intelligence?: Record<string, unknown> | null;
  verified_facts?: Record<string, unknown>[];
  missing_facts?: Record<string, unknown>[];
  campaign_context_id?: string | null;
  generation_context_id?: string | null;
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
  layout?: string | null;
  metrics?: Array<{
    id: string;
    type: string;
    display_value: string;
    label: string;
    raw_value?: number | string;
  }> | null;
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
    layout?: string;
    metrics?: Array<{
      id: string;
      type: string;
      display_value: string;
      label: string;
      raw_value?: number | string;
    }>;
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
  if (el.type === 'METRIC_GROUP') {
    return {
      ...base,
      role: 'metric_group',
      layout: el.layout ?? 'horizontal',
      metrics: Array.isArray(el.metrics)
        ? el.metrics.map((m) => ({
            id: m.id,
            type: m.type,
            display_value: m.display_value,
            label: m.label,
            raw_value: m.raw_value,
          }))
        : [],
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
  modeExplicit?: boolean;
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
  const mode = inferDesignMode(instruction, input.posts, input.mode, {
    explicit: Boolean(input.modeExplicit),
  });
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
      mode_explicit: Boolean(input.modeExplicit),
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
    structured_metrics: meta?.structured_metrics ?? [],
    metric_group: meta?.metric_group ?? null,
    creative_concept: meta?.creative_concept ?? null,
    creative_plan: meta?.creative_plan ?? null,
    design_quality: meta?.design_quality ?? null,
    validation: meta?.validation ?? null,
    marketing_strategy: meta?.marketing_strategy ?? null,
    copy_quality: meta?.copy_quality ?? null,
    headline_candidates: meta?.headline_candidates ?? [],
    campaign_intelligence: meta?.campaign_intelligence ?? null,
    verified_facts: meta?.verified_facts ?? [],
    missing_facts: meta?.missing_facts ?? [],
    campaign_context_id: meta?.campaign_context_id ?? null,
    generation_context_id: meta?.generation_context_id ?? null,
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
    structured_metrics: meta.structured_metrics ?? [],
    metric_group: meta.metric_group ?? null,
    creative_concept: meta.creative_concept ?? null,
    creative_plan: meta.creative_plan ?? null,
    design_quality: meta.design_quality ?? null,
    validation: meta.validation ?? null,
    marketing_strategy: meta.marketing_strategy ?? null,
    copy_quality: meta.copy_quality ?? null,
    headline_candidates: meta.headline_candidates ?? [],
    campaign_intelligence: meta.campaign_intelligence ?? null,
    verified_facts: meta.verified_facts ?? [],
    missing_facts: meta.missing_facts ?? [],
    campaign_context_id: meta.campaign_context_id ?? null,
    generation_context_id: meta.generation_context_id ?? null,
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
    structured_metrics: Array.isArray(raw.structured_metrics)
      ? raw.structured_metrics.filter((f): f is Record<string, unknown> => !!f && typeof f === 'object')
      : [],
    metric_group:
      raw.metric_group && typeof raw.metric_group === 'object' && !Array.isArray(raw.metric_group)
        ? (raw.metric_group as Record<string, unknown>)
        : null,
    creative_concept:
      raw.creative_concept && typeof raw.creative_concept === 'object' && !Array.isArray(raw.creative_concept)
        ? (raw.creative_concept as Record<string, unknown>)
        : null,
    creative_plan:
      raw.creative_plan && typeof raw.creative_plan === 'object' && !Array.isArray(raw.creative_plan)
        ? (raw.creative_plan as Record<string, unknown>)
        : null,
    design_quality:
      raw.design_quality && typeof raw.design_quality === 'object' && !Array.isArray(raw.design_quality)
        ? (raw.design_quality as Record<string, unknown>)
        : null,
    validation:
      raw.validation && typeof raw.validation === 'object' && !Array.isArray(raw.validation)
        ? (raw.validation as Record<string, unknown>)
        : null,
    marketing_strategy:
      raw.marketing_strategy && typeof raw.marketing_strategy === 'object' && !Array.isArray(raw.marketing_strategy)
        ? (raw.marketing_strategy as Record<string, unknown>)
        : null,
    copy_quality:
      raw.copy_quality && typeof raw.copy_quality === 'object' && !Array.isArray(raw.copy_quality)
        ? (raw.copy_quality as Record<string, unknown>)
        : null,
    headline_candidates: Array.isArray(raw.headline_candidates)
      ? raw.headline_candidates.filter((f): f is Record<string, unknown> => !!f && typeof f === 'object')
      : [],
    campaign_intelligence:
      raw.campaign_intelligence &&
      typeof raw.campaign_intelligence === 'object' &&
      !Array.isArray(raw.campaign_intelligence)
        ? (raw.campaign_intelligence as Record<string, unknown>)
        : null,
    verified_facts: Array.isArray(raw.verified_facts)
      ? raw.verified_facts.filter((f): f is Record<string, unknown> => !!f && typeof f === 'object')
      : [],
    missing_facts: Array.isArray(raw.missing_facts)
      ? raw.missing_facts.filter((f): f is Record<string, unknown> => !!f && typeof f === 'object')
      : [],
    campaign_context_id: typeof raw.campaign_context_id === 'string' ? raw.campaign_context_id : null,
    generation_context_id: typeof raw.generation_context_id === 'string' ? raw.generation_context_id : null,
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
