import {
  alignElementConstrained,
  constrainElement,
  growTextBoxToContent,
  type AlignMode,
} from './social-media-builder-layout';

/**
 * Persistent Social Media Builder canvas elements (TEXT | IMAGE | BUTTON).
 * Coordinates are absolute pixels in the post's format size.
 */

export type SocialTextAlign = 'left' | 'center' | 'right';
export type SocialElementType = 'TEXT' | 'IMAGE' | 'BUTTON' | 'METRIC_GROUP';
export type SocialTextRole = 'headline' | 'body' | 'custom' | 'eyebrow' | 'brand';
export type SocialMetricType =
  | 'currency'
  | 'percentage'
  | 'duration'
  | 'count'
  | 'yield'
  | 'return'
  | 'price'
  | 'generic_numeric';
export type SocialMetricLayout = 'horizontal' | 'stacked' | 'cards';
export type SocialMetricEmphasis = 'primary' | 'secondary' | 'tertiary';

export type SocialStructuredMetric = {
  id: string;
  type: SocialMetricType;
  raw_value: number | string;
  display_value: string;
  label: string;
  unit: string;
  locale: string;
  emphasis: SocialMetricEmphasis;
  source_token?: string;
};

export type SocialElementBase = {
  id: string;
  type: SocialElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
};

export type SocialTextElement = SocialElementBase & {
  type: 'TEXT';
  content: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold';
  align: SocialTextAlign;
  color: string;
  role: SocialTextRole;
};

export type SocialImageElement = SocialElementBase & {
  type: 'IMAGE';
  assetId: string | null;
  role?: 'image' | 'background' | 'cover' | 'logo';
};

export type SocialButtonElement = SocialElementBase & {
  type: 'BUTTON';
  label: string;
  backgroundColor: string;
  textColor: string;
  ctaStyle?: string | null;
};

export type SocialMetricGroupElement = SocialElementBase & {
  type: 'METRIC_GROUP';
  layout: SocialMetricLayout;
  metrics: SocialStructuredMetric[];
  color: string;
};

export type SocialElement =
  | SocialTextElement
  | SocialImageElement
  | SocialButtonElement
  | SocialMetricGroupElement;

const UUID_FRAGMENT = () =>
  `e-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

export function nextElementId(prefix = 'el'): string {
  return `${prefix}-${UUID_FRAGMENT()}`;
}

/** Ensure every element id is unique within a post (AI pending-* collisions break selection). */
export function ensureUniqueElementIds(elements: SocialElement[]): SocialElement[] {
  const seen = new Set<string>();
  return elements.map((el) => {
    const raw = typeof el.id === 'string' ? el.id.trim() : '';
    if (raw && !seen.has(raw)) {
      seen.add(raw);
      return el.id === raw ? el : { ...el, id: raw };
    }
    const prefix =
      el.type === 'TEXT'
        ? el.role === 'headline'
          ? 'headline'
          : el.role === 'body'
            ? 'body'
            : el.role === 'eyebrow'
              ? 'eyebrow'
              : 'text' : el.type === 'BUTTON' ? 'cta' : el.type === 'METRIC_GROUP' ? 'metrics' : 'img';
    let next = nextElementId(prefix);
    while (seen.has(next)) next = nextElementId(prefix);
    seen.add(next);
    return { ...el, id: next };
  });
}

export function createDefaultElements(
  width: number,
  height: number,
  opts?: { headline?: string; caption?: string; cta?: string },
): SocialElement[] {
  const w = Math.max(1, Math.round(width));
  const h = Math.max(1, Math.round(height));
  const margin = Math.max(24, Math.round(w * 0.07));
  const contentW = Math.max(40, w - margin * 2);
  const headlineSize = Math.max(22, Math.round(w * 0.055));
  const bodySize = Math.max(14, Math.round(w * 0.028));
  const ctaH = Math.max(36, Math.round(h * 0.045));
  const ctaW = Math.min(contentW, Math.max(160, Math.round(w * 0.38)));
  const headlineH = Math.round(headlineSize * 2.4);
  const bodyH = Math.round(bodySize * 3.2);

  return [
    {
      id: nextElementId('headline'),
      type: 'TEXT',
      role: 'headline',
      content: opts?.headline ?? 'New social post',
      fontSize: headlineSize,
      fontWeight: 'bold',
      align: 'center',
      color: '#ffffff',
      x: margin,
      y: Math.round(h * 0.22),
      width: contentW,
      height: headlineH,
      zIndex: 2,
    },
    {
      id: nextElementId('body'),
      type: 'TEXT',
      role: 'body',
      content: opts?.caption ?? '',
      fontSize: bodySize,
      fontWeight: 'normal',
      align: 'center',
      color: '#ffffff',
      x: margin,
      y: Math.round(h * 0.46),
      width: contentW,
      height: bodyH,
      zIndex: 3,
    },
    {
      id: nextElementId('cta'),
      type: 'BUTTON',
      label: opts?.cta ?? 'Schedule a private tour',
      backgroundColor: '#ffffff',
      textColor: '#111827',
      x: Math.round((w - ctaW) / 2),
      y: Math.min(h - margin - ctaH, Math.round(h * 0.88)),
      width: ctaW,
      height: ctaH,
      zIndex: 4,
    },
  ];
}

export function createTextElement(
  width: number,
  height: number,
  role: SocialTextRole = 'custom',
): SocialTextElement {
  const fontSize = role === 'headline' ? Math.max(22, Math.round(width * 0.05)) : 24;
  return {
    id: nextElementId('text'),
    type: 'TEXT',
    role,
    content: role === 'headline' ? 'Headline' : 'Body text',
    fontSize,
    fontWeight: role === 'headline' ? 'bold' : 'normal',
    align: 'center',
    color: '#ffffff',
    x: Math.round(width * 0.1),
    y: Math.round(height * 0.4),
    width: Math.round(width * 0.8),
    height: Math.round(fontSize * 2.5),
    zIndex: 10,
  };
}

export function createButtonElement(width: number, height: number): SocialButtonElement {
  const btnW = Math.min(Math.round(width * 0.4), 420);
  const btnH = Math.max(40, Math.round(height * 0.05));
  return {
    id: nextElementId('btn'),
    type: 'BUTTON',
    label: 'Call to action',
    backgroundColor: '#ffffff',
    textColor: '#111827',
    x: Math.round((width - btnW) / 2),
    y: Math.round(height * 0.55),
    width: btnW,
    height: btnH,
    zIndex: 10,
  };
}

export function createImageElement(
  width: number,
  height: number,
  assetId: string | null,
): SocialImageElement {
  const box = Math.round(Math.min(width, height) * 0.35);
  return {
    id: nextElementId('img'),
    type: 'IMAGE',
    assetId,
    x: Math.round((width - box) / 2),
    y: Math.round((height - box) / 2),
    width: box,
    height: box,
    zIndex: 10,
  };
}

export function duplicateElement(el: SocialElement, canvasW = 1080, canvasH = 1080): SocialElement {
  const clone: SocialElement = {
    ...el,
    id: nextElementId('copy'),
    x: el.x + 24,
    y: el.y + 24,
    zIndex: el.zIndex + 1,
  };
  return { ...clone, ...constrainElement(clone, canvasW, canvasH) };
}

export function sortElementsByZ(elements: SocialElement[]): SocialElement[] {
  return [...elements].sort((a, b) => a.zIndex - b.zIndex || a.id.localeCompare(b.id));
}

export function bringElementForward(
  elements: SocialElement[],
  elementId: string,
): SocialElement[] {
  const sorted = sortElementsByZ(elements);
  const idx = sorted.findIndex((e) => e.id === elementId);
  if (idx < 0 || idx >= sorted.length - 1) return elements;
  const current = sorted[idx]!;
  const above = sorted[idx + 1]!;
  return elements.map((e) => {
    if (e.id === current.id) return { ...e, zIndex: above.zIndex + 1 };
    return e;
  });
}

export function sendElementBackward(
  elements: SocialElement[],
  elementId: string,
): SocialElement[] {
  const sorted = sortElementsByZ(elements);
  const idx = sorted.findIndex((e) => e.id === elementId);
  if (idx <= 0) return elements;
  const current = sorted[idx]!;
  const below = sorted[idx - 1]!;
  return elements.map((e) => {
    if (e.id === current.id) return { ...e, zIndex: Math.max(0, below.zIndex - 1) };
    return e;
  });
}

export function alignElement(
  el: SocialElement,
  mode: AlignMode,
  artboardW: number,
  artboardH: number,
): SocialElement {
  return alignElementConstrained(el, mode, artboardW, artboardH);
}

export function headlineFromElements(elements: SocialElement[]): string {
  const hit = elements.find(
    (e): e is SocialTextElement => e.type === 'TEXT' && e.role === 'headline',
  );
  if (hit) return hit.content;
  const any = elements.find((e): e is SocialTextElement => e.type === 'TEXT');
  return any?.content ?? '';
}

export function captionFromElements(elements: SocialElement[]): string {
  const hit = elements.find(
    (e): e is SocialTextElement => e.type === 'TEXT' && e.role === 'body',
  );
  if (hit) return hit.content;
  const texts = elements.filter((e): e is SocialTextElement => e.type === 'TEXT');
  return texts.length > 1 ? texts[1]!.content : '';
}

export function ctaFromElements(elements: SocialElement[]): string {
  const btn = elements.find((e): e is SocialButtonElement => e.type === 'BUTTON');
  return btn?.label ?? '';
}

export function applyCopyToElements(
  elements: SocialElement[],
  copy: { headline?: string; caption?: string; cta?: string },
): SocialElement[] {
  let appliedHeadline = false;
  let appliedBody = false;
  let appliedCta = false;
  const next = elements.map((el) => {
    if (el.type === 'TEXT' && el.role === 'headline' && copy.headline != null) {
      appliedHeadline = true;
      return { ...el, content: copy.headline };
    }
    if (el.type === 'TEXT' && el.role === 'body' && copy.caption != null) {
      appliedBody = true;
      return { ...el, content: copy.caption };
    }
    if (el.type === 'BUTTON' && copy.cta != null) {
      appliedCta = true;
      return { ...el, label: copy.cta };
    }
    return el;
  });

  const extras: SocialElement[] = [];
  const maxZ = next.reduce((m, e) => Math.max(m, e.zIndex), 0);
  if (copy.headline != null && !appliedHeadline) {
    const el = createTextElement(1080, 1080, 'headline');
    el.content = copy.headline;
    el.zIndex = maxZ + 1;
    extras.push(el);
  }
  if (copy.caption != null && !appliedBody) {
    const el = createTextElement(1080, 1080, 'body');
    el.content = copy.caption;
    el.zIndex = maxZ + 2;
    extras.push(el);
  }
  if (copy.cta != null && !appliedCta) {
    const el = createButtonElement(1080, 1080);
    el.label = copy.cta;
    el.zIndex = maxZ + 3;
    extras.push(el);
  }
  const merged = extras.length ? [...next, ...extras] : next;
  return merged.map((el) => {
    if (el.type !== 'TEXT') return el;
    const contentChanged =
      (el.role === 'headline' && copy.headline != null) ||
      (el.role === 'body' && copy.caption != null) ||
      extras.some((x) => x.id === el.id);
    if (!contentChanged) return el;
    return growTextBoxToContent(el, 1080, 1080);
  });
}

export const P0_BOTTOM_ACTIONS = new Set(['addComponent', 'text', 'image', 'button']);
export const P0_COMPONENT_KEYS = new Set([
  'title',
  'text',
  'image',
  'button',
  'cta',
]);

/**
 * Normalize any stored/AI color to `#rrggbb` for `<input type="color">`.
 * Short (#rgb) / alpha (#rrggbbaa) hex values crash React color inputs.
 */
export function toColorInputValue(value: string | null | undefined, fallback = '#ffffff'): string {
  const raw = typeof value === 'string' ? value.trim() : '';
  if (/^#[0-9a-fA-F]{6}$/.test(raw)) return raw.toLowerCase();
  if (/^#[0-9a-fA-F]{8}$/.test(raw)) return `#${raw.slice(1, 7).toLowerCase()}`;
  if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
    const r = raw[1]!;
    const g = raw[2]!;
    const b = raw[3]!;
    return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
  }
  // Named / rgb() / invalid values crash <input type="color"> — always fall back.
  return /^#[0-9a-fA-F]{6}$/.test(fallback) ? fallback.toLowerCase() : '#ffffff';
}
