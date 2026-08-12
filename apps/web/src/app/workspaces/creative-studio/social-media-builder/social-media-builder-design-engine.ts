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

const EDIT_HINTS = [
  'değiştir',
  'güncelle',
  'edit',
  'update',
  'move',
  'resize',
  'replace',
  'renk',
  'color',
  'taşı',
  'tasi',
  'büyüt',
  'küçült',
  'kucult',
  'ortala',
  'align',
  'arka plan',
  'background',
  'başlığı',
  'basligi',
  'başlık',
  'cta',
  'buton',
  'görsel',
  'gorsel',
  'yukarı',
  'yukari',
  'aşağı',
  'asagi',
  'sola',
  'sağa',
  'saga',
  'beyaz',
  'siyah',
  'bulut',
  'exterior',
  'kullan',
  'ferahlat',
  'premium',
  'sade',
  'binayı',
  'binayi',
  'gökyüz',
  'gokyuz',
  'tek satır',
  'tek satir',
  'büyük',
  'buyuk',
];

export type DesignGenerationMeta = SocialGenerationMeta & {
  brand_context_status?: string;
  mode?: SocialDesignMode;
  planner?: string;
  ops_count?: number;
};

export type BuildSocialDesignResult =
  | { ok: true; request: SocialDesignRequest }
  | { ok: false; reason: 'missing_project' | 'missing_instruction' };

export function inferDesignMode(
  instruction: string,
  posts: SocialPost[],
  preferred?: SocialDesignMode | null,
): SocialDesignMode {
  if (preferred === 'create' || preferred === 'edit') {
    if (preferred === 'edit' && posts.length === 0) return 'create';
    return preferred;
  }
  const instr = (instruction || '').toLowerCase();
  if (posts.length > 0 && EDIT_HINTS.some((h) => instr.includes(h))) return 'edit';
  if (posts.length === 0) return 'create';
  // Default: create a new post unless clearly editing
  return 'create';
}

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
