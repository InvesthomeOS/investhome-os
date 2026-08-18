/**
 * Social Media Builder follow-up AI edits on existing layered post data.
 *
 * Working commands (TR / EN):
 * - shrink_headline — "başlığı küçült", "shrink headline", "smaller headline"
 * - simplify_text — "daha minimal", "yazıları daha sade", "simplify text"
 * - remove_price — "fiyatı kaldır", "remove price"
 * - make_premium — "daha premium yap", "make it more premium"
 * - use_night_render — "gece renderını kullan", "use night render" (needs a night-tagged media asset)
 * - move_logo_down — "logoyu biraz aşağı al", "move logo down" (needs an IMAGE logo layer)
 * - move_headline_down — "başlığı biraz aşağı al", "move headline down" (y-only; preserves fontSize)
 * - move_headline_up — "başlığı yukarı al", "move headline up" (y-only; preserves fontSize)
 * - gold_cta — "cta gold", "altın cta" (CTA colors only)
 *
 * Unrecognized instructions are not applied here — the workspace may send them
 * to the existing generate/edit API. Matched-but-impossible commands must toast,
 * never pretend success.
 */

import { growTextBoxToContent, resolveCollisions } from './social-media-builder-layout';
import type { SocialElement, SocialTextElement } from './social-media-builder-elements';
import type { SocialPost } from './social-media-builder-model';

export type AiFollowUpCommand =
  | 'shrink_headline'
  | 'simplify_text'
  | 'remove_price'
  | 'make_premium'
  | 'use_night_render'
  | 'move_logo_down'
  | 'move_headline_down'
  | 'move_headline_up'
  | 'gold_cta';

export type AiFollowUpMediaHint = {
  id: string;
  name?: string | null;
  tags?: string[] | null;
  folderCategory?: string | null;
};

export type AiFollowUpFailureReason =
  | 'unrecognized'
  | 'no_headline'
  | 'no_price'
  | 'no_night_asset'
  | 'no_logo'
  | 'no_text'
  | 'no_cta';

export type AiFollowUpResult =
  | { ok: true; commands: AiFollowUpCommand[]; post: SocialPost }
  | { ok: false; commands: AiFollowUpCommand[]; reason: AiFollowUpFailureReason };

const PRICE_RE =
  /(?:[$€£₺]\s?\d|\d[\d.,]*\s?(?:\$|€|£|₺|usd|eur|try)|fiyat|price|asking|starting from|başlangıç|satış fiyat|m[ıi]lyon|million)/i;

const NIGHT_RE = /night|nighttime|gece|evening|dusk|twilight|ak[sş]am/i;

const COMMAND_PATTERNS: { command: AiFollowUpCommand; pattern: RegExp }[] = [
  { command: 'shrink_headline', pattern: /ba[sş]l[iı][gğ][iı].{0,24}k[uü][cç][uü]lt|shrink (the )?headline|smaller headline|headline.{0,12}(smaller|k[uü][cç][uü]k)/i },
  { command: 'remove_price', pattern: /fiyat[iı] kald[iı]r|remove (the )?price|hide (the )?price|fiyat[iı] gizle/i },
  { command: 'use_night_render', pattern: /gece render|night render|use (the )?night|gece g[oö]r[uü]n/i },
  { command: 'move_logo_down', pattern: /logoyu.{0,24}a[sş]a[gğ][iı]|move (the )?logo down|logo.{0,12}down/i },
  { command: 'move_headline_up', pattern: /ba[sş]l[iı][gğ][iı].{0,24}yukar[iı]|move (the )?headline up|headline.{0,12}up/i },
  { command: 'move_headline_down', pattern: /ba[sş]l[iı][gğ][iı].{0,24}a[sş]a[gğ][iı]|move (the )?headline down|headline.{0,12}down/i },
  { command: 'gold_cta', pattern: /gold cta|cta.{0,12}gold|alt[iı]n (cta|buton)|cta.{0,12}alt[iı]n|cta.?gold|gold.?cta/i },
  { command: 'make_premium', pattern: /daha premium|more premium|make (it )?premium/i },
  { command: 'simplify_text', pattern: /daha (minimal|sade)|yaz[iı]lar[iı].{0,16}sade|simplify (the )?text|more minimal|sadele[sş]tir/i },
];

export function parseAiFollowUpCommands(instruction: string): AiFollowUpCommand[] {
  const text = (instruction || '').trim();
  if (!text) return [];
  const found: AiFollowUpCommand[] = [];
  for (const row of COMMAND_PATTERNS) {
    if (row.pattern.test(text) && !found.includes(row.command)) found.push(row.command);
  }
  return found;
}

export function isNightMediaHint(item: AiFollowUpMediaHint): boolean {
  const hay = `${item.name ?? ''} ${(item.tags ?? []).join(' ')} ${item.folderCategory ?? ''}`;
  return NIGHT_RE.test(hay);
}

function headlineEl(elements: SocialElement[]): SocialTextElement | null {
  return elements.find((el): el is SocialTextElement => el.type === 'TEXT' && el.role === 'headline') ?? null;
}

function bodyEl(elements: SocialElement[]): SocialTextElement | null {
  return elements.find((el): el is SocialTextElement => el.type === 'TEXT' && el.role === 'body') ?? null;
}

function logoEl(elements: SocialElement[]): SocialElement | null {
  const named = elements.find((el) => el.type === 'IMAGE' && el.role === 'logo');
  if (named) return named;
  const images = elements.filter((el) => el.type === 'IMAGE' && el.role !== 'background' && el.role !== 'cover');
  const small = images
    .filter((el) => el.width * el.height < 220 * 220)
    .sort((a, b) => a.width * a.height - b.width * b.height);
  return small[0] ?? null;
}

function looksLikePriceText(text: string): boolean {
  return PRICE_RE.test(text || '');
}

function firstSentence(text: string): string {
  const raw = (text || '').replace(/\s+/g, ' ').trim();
  if (!raw) return '';
  const cut = raw.match(/^(.+?[.!?])(?:\s|$)/);
  const sentence = (cut?.[1] || raw).trim();
  return sentence.length > 140 ? `${sentence.slice(0, 137).trimEnd()}…` : sentence;
}

function refitText(el: SocialTextElement, canvasW: number, canvasH: number): SocialTextElement {
  return growTextBoxToContent(el, canvasW, canvasH);
}

function applyShrinkHeadline(elements: SocialElement[], canvasW: number, canvasH: number): SocialElement[] | null {
  const target = headlineEl(elements);
  if (!target) return null;
  const nextSize = Math.max(18, Math.round(target.fontSize * 0.72));
  return elements.map((el) => {
    if (el.id !== target.id || el.type !== 'TEXT') return el;
    return refitText({ ...el, fontSize: nextSize }, canvasW, canvasH);
  });
}

function applySimplifyText(elements: SocialElement[], canvasW: number, canvasH: number): SocialElement[] | null {
  const body = bodyEl(elements);
  const extras = elements.filter((el): el is SocialTextElement => el.type === 'TEXT' && el.role === 'custom');
  if (!body && extras.length === 0) return null;
  return elements.map((el) => {
    if (el.type !== 'TEXT') return el;
    if (el.role === 'body' || el.role === 'custom') {
      const simplified = firstSentence(el.content);
      if (simplified === el.content) return el;
      return refitText({ ...el, content: simplified, fontWeight: 'normal' }, canvasW, canvasH);
    }
    return el;
  });
}

function applyRemovePrice(elements: SocialElement[]): SocialElement[] | null {
  const next = elements.filter((el) => {
    if (el.type === 'METRIC_GROUP') return false;
    if (el.type === 'TEXT' && looksLikePriceText(el.content)) return false;
    if (el.type === 'BUTTON' && looksLikePriceText(el.label)) return false;
    return true;
  });
  return next.length === elements.length ? null : next;
}

function applyMakePremium(elements: SocialElement[], canvasW: number, canvasH: number): SocialElement[] {
  return elements.map((el) => {
    if (el.type === 'TEXT' && el.role === 'headline') {
      const size = Math.max(20, Math.min(el.fontSize, Math.round(el.fontSize * 0.9)));
      return refitText(
        { ...el, fontSize: size, fontWeight: 'bold', color: '#ffffff' },
        canvasW,
        canvasH,
      );
    }
    if (el.type === 'TEXT' && (el.role === 'body' || el.role === 'custom')) {
      const simplified = firstSentence(el.content);
      return refitText(
        { ...el, content: simplified, fontWeight: 'normal', fontSize: Math.max(14, Math.round(el.fontSize * 0.92)) },
        canvasW,
        canvasH,
      );
    }
    if (el.type === 'BUTTON') {
      return { ...el, backgroundColor: '#ffffff', textColor: '#111827' };
    }
    return el;
  });
}

function applyMoveLogoDown(elements: SocialElement[], canvasH: number): SocialElement[] | null {
  const logo = logoEl(elements);
  if (!logo) return null;
  const delta = Math.max(18, Math.round(canvasH * 0.04));
  return elements.map((el) => {
    if (el.id !== logo.id) return el;
    const y = Math.min(canvasH - el.height - 8, el.y + delta);
    // Position-only patch — preserve size/opacity and any sibling style fields.
    return { ...el, y };
  });
}

/** Move headline down without rewriting typography (manual fontSize must survive). */
function applyMoveHeadlineDown(elements: SocialElement[], canvasH: number): SocialElement[] | null {
  const target = headlineEl(elements);
  if (!target) return null;
  const delta = Math.max(18, Math.round(canvasH * 0.04));
  return elements.map((el) => {
    if (el.id !== target.id || el.type !== 'TEXT') return el;
    const y = Math.min(canvasH - el.height - 8, el.y + delta);
    return { ...el, y };
  });
}

/** Move headline up without rewriting typography (manual fontSize must survive). */
function applyMoveHeadlineUp(elements: SocialElement[]): SocialElement[] | null {
  const target = headlineEl(elements);
  if (!target) return null;
  const delta = Math.max(18, Math.round((target.y + target.height) * 0.08) || 24);
  return elements.map((el) => {
    if (el.id !== target.id || el.type !== 'TEXT') return el;
    const y = Math.max(8, el.y - delta);
    return { ...el, y };
  });
}

/** Gold CTA — style only. Do not move or resize. */
function applyGoldCta(elements: SocialElement[]): SocialElement[] | null {
  const cta = elements.find((el) => el.type === 'BUTTON');
  if (!cta) return null;
  return elements.map((el) => {
    if (el.id !== cta.id || el.type !== 'BUTTON') return el;
    return { ...el, backgroundColor: '#C4A35A', textColor: '#1B2A4A', ctaStyle: 'gold' };
  });
}

function patchCoverAsset(post: SocialPost, assetId: string): SocialPost {
  return {
    ...post,
    coverAssetId: assetId,
    elements: post.elements.map((el) =>
      el.type === 'IMAGE' && (el.role === 'background' || el.role === 'cover' || el.role === 'image')
        ? { ...el, assetId }
        : el,
    ),
  };
}

export function applyAiFollowUpEdit(
  post: SocialPost,
  instruction: string,
  mediaItems: AiFollowUpMediaHint[] = [],
): AiFollowUpResult {
  const commands = parseAiFollowUpCommands(instruction);
  if (!commands.length) {
    return { ok: false, commands: [], reason: 'unrecognized' };
  }

  const canvasW = Math.max(8, post.width || 1080);
  const canvasH = Math.max(8, post.height || 1080);
  let elements = post.elements.map((el) => ({ ...el }));
  let nextPost = post;
  const applied: AiFollowUpCommand[] = [];

  for (const command of commands) {
    if (command === 'shrink_headline') {
      const next = applyShrinkHeadline(elements, canvasW, canvasH);
      if (!next) return { ok: false, commands, reason: 'no_headline' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'simplify_text') {
      const next = applySimplifyText(elements, canvasW, canvasH);
      if (!next) return { ok: false, commands, reason: 'no_text' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'remove_price') {
      const next = applyRemovePrice(elements);
      if (!next) return { ok: false, commands, reason: 'no_price' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'make_premium') {
      elements = applyMakePremium(elements, canvasW, canvasH);
      applied.push(command);
      continue;
    }
    if (command === 'move_logo_down') {
      const next = applyMoveLogoDown(elements, canvasH);
      if (!next) return { ok: false, commands, reason: 'no_logo' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'move_headline_down') {
      const next = applyMoveHeadlineDown(elements, canvasH);
      if (!next) return { ok: false, commands, reason: 'no_headline' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'move_headline_up') {
      const next = applyMoveHeadlineUp(elements);
      if (!next) return { ok: false, commands, reason: 'no_headline' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'gold_cta') {
      const next = applyGoldCta(elements);
      if (!next) return { ok: false, commands, reason: 'no_cta' };
      elements = next;
      applied.push(command);
      continue;
    }
    if (command === 'use_night_render') {
      const currentId = post.coverAssetId;
      const night = mediaItems.find((item) => item.id && item.id !== currentId && isNightMediaHint(item));
      if (!night?.id) return { ok: false, commands, reason: 'no_night_asset' };
      nextPost = patchCoverAsset(nextPost, night.id);
      applied.push(command);
    }
  }

  const laidOut = resolveCollisions(elements, canvasW, canvasH);
  return {
    ok: true,
    commands: applied,
    post: {
      ...nextPost,
      elements: laidOut,
      headline: headlineEl(laidOut)?.content || nextPost.headline,
      caption: bodyEl(laidOut)?.content || nextPost.caption,
      updatedAt: new Date().toISOString(),
    },
  };
}
