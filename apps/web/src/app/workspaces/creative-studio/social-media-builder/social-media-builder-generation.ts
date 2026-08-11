/**
 * Social Media Builder ↔ shared Creative Studio generation helpers.
 * Asset IDs only — never Drive URLs or mock media.
 */

import type {
  CreativeStudioCitation,
  CreativeStudioGenerateRequest,
  CreativeStudioGenerateResponse,
} from '@/lib/api/creative-studio';

import { isMediaAssetUuid, type CsImageRef } from '../_components/cs-image-ref';

import type { PlatformKey, SocialPost } from './social-media-builder-model';
import {
  applyCopyToElements,
  captionFromElements,
  ctaFromElements,
  headlineFromElements,
} from './social-media-builder-elements';

export type SocialGenerationMeta = {
  citations: CreativeStudioCitation[];
  warnings: string[];
  grounded: boolean;
  retrieval_confidence: number;
  asset_ids_used: string[];
  provider: string;
  model: string;
};

export type BuildSocialGenerateResult =
  | { ok: true; request: CreativeStudioGenerateRequest }
  | { ok: false; reason: 'missing_project' | 'missing_instruction' };

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function collectSelectedAssetIds(
  coverImage?: CsImageRef | null,
  galleryImages?: CsImageRef[] | null,
): string[] {
  const ids: string[] = [];
  const seen = new Set<string>();
  const push = (raw: string | null | undefined) => {
    if (!raw || !isMediaAssetUuid(raw)) return;
    const id = raw.trim();
    if (seen.has(id)) return;
    seen.add(id);
    ids.push(id);
  };
  push(coverImage?.asset_id);
  for (const ref of galleryImages ?? []) {
    push(ref?.asset_id);
  }
  return ids;
}

/** Reject anything that looks like a URL slipping into asset id slots. */
export function assertNoRawMediaUrls(assetIds: string[]): boolean {
  return assetIds.every((id) => {
    if (!id || typeof id !== 'string') return false;
    const trimmed = id.trim();
    if (/^https?:\/\//i.test(trimmed) || /drive\.google/i.test(trimmed)) return false;
    return UUID_RE.test(trimmed);
  });
}

export function buildSocialGenerateRequest(input: {
  linkedProjectId: string | null | undefined;
  instruction: string;
  coverImage?: CsImageRef | null;
  galleryImages?: CsImageRef[] | null;
  language?: string | null;
  platforms?: Iterable<PlatformKey | string>;
  formatPreset?: string | null;
  platform?: string | null;
  postName?: string | null;
  format?: string | null;
}): BuildSocialGenerateResult {
  const linked = typeof input.linkedProjectId === 'string' ? input.linkedProjectId.trim() : '';
  if (!linked || !UUID_RE.test(linked)) {
    return { ok: false, reason: 'missing_project' };
  }
  const instruction = (input.instruction || '').trim();
  if (!instruction) {
    return { ok: false, reason: 'missing_instruction' };
  }

  const selected_asset_ids = collectSelectedAssetIds(input.coverImage, input.galleryImages);
  if (!assertNoRawMediaUrls(selected_asset_ids)) {
    // Defensive: drop invalid entries rather than sending URLs.
    const cleaned = selected_asset_ids.filter((id) => UUID_RE.test(id) && !/^https?:/i.test(id));
    return {
      ok: true,
      request: finishRequest(linked, instruction, cleaned, input),
    };
  }

  return {
    ok: true,
    request: finishRequest(linked, instruction, selected_asset_ids, input),
  };
}

function finishRequest(
  linkedProjectId: string,
  instruction: string,
  selected_asset_ids: string[],
  input: {
    language?: string | null;
    platforms?: Iterable<PlatformKey | string>;
    formatPreset?: string | null;
    platform?: string | null;
    postName?: string | null;
    format?: string | null;
  },
): CreativeStudioGenerateRequest {
  const platforms = input.platforms
    ? Array.from(input.platforms).map(String).filter(Boolean)
    : [];
  const builder_context: Record<string, unknown> = {
    builder: 'social',
  };
  if (platforms.length) builder_context.platforms = platforms;
  if (input.formatPreset) builder_context.format_preset = input.formatPreset;
  if (input.format) builder_context.format = input.format;
  if (input.platform) builder_context.platform = input.platform;
  if (input.postName) builder_context.post_name = input.postName;

  return {
    linked_project_id: linkedProjectId,
    builder_type: 'social',
    instruction,
    selected_asset_ids,
    language: input.language?.trim() || null,
    builder_context,
  };
}

export function defaultSocialInstruction(post: Pick<SocialPost, 'name' | 'platform' | 'format'>): string {
  const bits = [
    'Write platform-ready social post copy (headline and caption)',
    post.platform ? `for ${post.platform}` : null,
    post.format ? `(${post.format})` : null,
    post.name ? `titled "${post.name}"` : null,
    'using only verified project knowledge.',
  ].filter(Boolean);
  return bits.join(' ');
}

export function applyGeneratedCopyToPost(content: string): {
  headline?: string;
  caption?: string;
  description?: string;
  cta?: string;
} {
  const text = (content || '').trim();
  if (!text) return {};
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  const first = lines[0] ?? text;
  const rest = lines.slice(1).join('\n').trim();
  const headline = first.length <= 120 ? first : first.slice(0, 117).trimEnd() + '…';
  const caption = rest || text;
  let cta: string | undefined;
  const last = lines[lines.length - 1];
  if (
    last &&
    last !== first &&
    last.length <= 48 &&
    /^(book|schedule|learn|discover|join|get|contact|rezerv|hemen|keşfet)/i.test(last)
  ) {
    cta = last;
  }
  return {
    headline,
    caption,
    description: text,
    ...(cta ? { cta } : {}),
  };
}

/** Apply AI copy onto persistent TEXT / BUTTON elements (same canvas model). */
export function applyGeneratedCopyToElements(
  elements: SocialPost['elements'],
  content: string,
): SocialPost['elements'] {
  const copy = applyGeneratedCopyToPost(content);
  if (!copy.headline && !copy.caption) return elements;
  return applyCopyToElements(elements, {
    headline: copy.headline,
    caption: copy.caption,
    cta: copy.cta,
  });
}

export function syncPostCopyFields(post: SocialPost): SocialPost {
  return {
    ...post,
    headline: headlineFromElements(post.elements) || post.headline,
    caption: captionFromElements(post.elements) || post.caption,
  };
}

export function peekCtaLabel(post: SocialPost): string {
  return ctaFromElements(post.elements);
}

export function hasInsufficientContext(
  response: Pick<CreativeStudioGenerateResponse, 'warnings' | 'grounded'>,
): boolean {
  if (response.grounded === false) return true;
  const warnings = response.warnings ?? [];
  return warnings.some(
    (w) =>
      w === 'insufficient_context' ||
      w === 'insufficient_retrieved_content' ||
      w.includes('insufficient'),
  );
}

export function toGenerationMeta(
  response: CreativeStudioGenerateResponse,
): SocialGenerationMeta {
  return {
    citations: response.citations ?? [],
    warnings: response.warnings ?? [],
    grounded: Boolean(response.grounded),
    retrieval_confidence: response.retrieval_confidence ?? 0,
    asset_ids_used: response.asset_ids_used ?? [],
    provider: response.provider,
    model: response.model,
  };
}
