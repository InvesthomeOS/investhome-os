/**
 * Deterministic Layout Intelligence (client mirror of API layout.py).
 * One geometry path for manual move/resize/align/duplicate/format + AI draft merge.
 */

import {
  isBoldishWeight,
  type SocialElement,
  type SocialMetricGroupElement,
  type SocialMetricLayout,
  type SocialStructuredMetric,
  type SocialTextElement,
} from './social-media-builder-elements';

export const SAFE_MARGIN_RATIO = 0.07;
export const LINE_HEIGHT = 1.2;
const AVG_CHAR_RATIO_NORMAL = 0.52;
const AVG_CHAR_RATIO_BOLD = 0.58;
/** Metric values are display figures — prefer tabular bold tracking. */
const METRIC_VALUE_CHAR_RATIO = 0.66;
const METRIC_LABEL_CHAR_RATIO = 0.55;

export type AlignMode =
  | 'left'
  | 'center'
  | 'right'
  | 'top'
  | 'middle'
  | 'bottom'
  | 'vcenter'
  | 'safe-area'
  | 'hcenter';

function finiteNum(n: unknown, fallback: number): number {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}

function clampInt(value: unknown, lo: number, hi: number, fallback: number): number {
  const n = Math.round(finiteNum(value, fallback));
  return Math.max(lo, Math.min(hi, n));
}

export function safeContentBox(canvasW: number, canvasH: number) {
  const mx = Math.max(24, Math.round(canvasW * SAFE_MARGIN_RATIO));
  const my = Math.max(24, Math.round(canvasH * SAFE_MARGIN_RATIO));
  return {
    x: mx,
    y: my,
    width: Math.max(40, canvasW - mx * 2),
    height: Math.max(40, canvasH - my * 2),
  };
}

export function constrainElement(
  el: Pick<SocialElement, 'type' | 'x' | 'y' | 'width' | 'height'> & { type: string },
  canvasW: number,
  canvasH: number,
): { x: number; y: number; width: number; height: number } {
  const fullBleed = el.type === 'IMAGE';
  const isButton = el.type === 'BUTTON';
  const isMetricGroup = el.type === 'METRIC_GROUP';
  const isShape = el.type === 'SHAPE';

  if (fullBleed) {
    const w = clampInt(el.width, 8, canvasW, Math.min(200, canvasW));
    const h = clampInt(el.height, 8, canvasH, Math.min(80, canvasH));
    return {
      x: clampInt(el.x, 0, Math.max(0, canvasW - w), 0),
      y: clampInt(el.y, 0, Math.max(0, canvasH - h), 0),
      width: w,
      height: h,
    };
  }

  if (isShape) {
    const w = clampInt(el.width, 2, canvasW, Math.min(80, canvasW));
    const h = clampInt(el.height, 2, canvasH, Math.min(8, canvasH));
    return {
      x: clampInt(el.x, 0, Math.max(0, canvasW - w), 0),
      y: clampInt(el.y, 0, Math.max(0, canvasH - h), 0),
      width: w,
      height: h,
    };
  }

  if (isButton || isMetricGroup) {
    const pad = 24;
    const maxW = Math.max(8, canvasW - pad * 2);
    const maxH = Math.max(8, canvasH - pad * 2);
    const w = clampInt(el.width, 8, maxW, Math.min(200, maxW));
    const h = clampInt(el.height, 8, maxH, Math.min(48, maxH));
    return {
      x: clampInt(el.x, pad, Math.max(pad, canvasW - w - pad), pad),
      y: clampInt(el.y, pad, Math.max(pad, canvasH - h - pad), pad),
      width: w,
      height: h,
    };
  }

  const box = safeContentBox(canvasW, canvasH);
  const w = clampInt(el.width, 8, box.width, Math.min(200, box.width));
  const h = clampInt(el.height, 8, box.height, Math.min(80, box.height));
  const maxX = box.x + box.width - w;
  const maxY = box.y + box.height - h;
  return {
    x: clampInt(el.x, box.x, Math.max(box.x, maxX), box.x),
    y: clampInt(el.y, box.y, Math.max(box.y, maxY), box.y),
    width: w,
    height: h,
  };
}

function charRatio(bold: boolean) {
  return bold ? AVG_CHAR_RATIO_BOLD : AVG_CHAR_RATIO_NORMAL;
}

function wrapParagraph(
  paragraph: string,
  maxChars: number,
): string[] {
  const words = paragraph.split(/\s+/).filter(Boolean);
  if (!words.length) return [''];
  const lines: string[] = [];
  let current = words[0]!;
  for (let i = 1; i < words.length; i++) {
    const word = words[i]!;
    const candidate = `${current} ${word}`;
    if (candidate.length <= maxChars) {
      current = candidate;
    } else {
      lines.push(current);
      current = word;
      while (current.length > maxChars) {
        lines.push(current.slice(0, maxChars));
        current = current.slice(maxChars);
      }
    }
  }
  lines.push(current);
  return lines;
}

/** Explicit user/AI `\n` are hard line breaks; spaces still wrap within each paragraph. */
export function estimateWrapLines(
  text: string,
  fontSize: number,
  maxWidth: number,
  bold = false,
): string[] {
  const raw = String(text ?? '');
  if (!raw) return [];
  const paragraphs = raw.split(/\r?\n/);
  if (fontSize <= 0 || maxWidth <= 0) return paragraphs;
  const charW = Math.max(1, fontSize * charRatio(bold));
  const maxChars = Math.max(1, Math.floor(maxWidth / charW));
  const lines: string[] = [];
  for (const para of paragraphs) {
    lines.push(...wrapParagraph(para, maxChars));
  }
  return lines;
}

export function explicitLineCount(text: string): number {
  const raw = String(text ?? '');
  if (!raw) return 0;
  return raw.split(/\r?\n/).length;
}

/**
 * While TEXT edit mode is active, canvas shortcuts must not run.
 * Escape is the only canvas-owned key (exit edit). Enter/arrows/delete/undo stay with the editor.
 */
export function canvasShortcutBlockedByTextEdit(editing: boolean, key: string): boolean {
  return Boolean(editing) && key !== 'Escape';
}

export function measureTextBlock(
  text: string,
  fontSize: number,
  maxWidth: number,
  bold = false,
): { lines: number; height: number; contentWidth: number } {
  const wrapped = estimateWrapLines(text, fontSize, maxWidth, bold);
  if (!wrapped.length) return { lines: 0, height: 0, contentWidth: 0 };
  const height = Math.round(wrapped.length * fontSize * LINE_HEIGHT);
  const charW = Math.max(1, fontSize * charRatio(bold));
  const contentWidth = Math.round(Math.max(...wrapped.map((l) => l.length)) * charW);
  return { lines: wrapped.length, height, contentWidth };
}

export type MetricGroupDensity = 'comfortable' | 'compact';

export type MetricGroupPresentation = {
  /** Persisted / requested layout after least-disruptive fallback. */
  layout: SocialMetricLayout;
  /** Visual density within horizontal family (not a separate user layout). */
  density: MetricGroupDensity;
  valueFontSize: number;
  labelFontSize: number;
  gutter: number;
  columnWidth: number;
  valueRowHeight: number;
  labelRowMinHeight: number;
  valuesSingleLine: boolean;
  columnCount: number;
};

function estimateMetricValueWidth(text: string, fontSize: number): number {
  const t = (text || '').trim();
  if (!t) return 0;
  return Math.ceil(t.length * Math.max(1, fontSize * METRIC_VALUE_CHAR_RATIO));
}

function estimateMetricLabelWidth(text: string, fontSize: number): number {
  const t = (text || '').trim();
  if (!t) return 0;
  // Uppercase tracking in CSS ≈ +4% — bake a small pad into measurement.
  return Math.ceil(t.length * Math.max(1, fontSize * METRIC_LABEL_CHAR_RATIO) * 1.04);
}

function metricValuesFitSingleLine(
  metrics: SocialStructuredMetric[],
  fontSize: number,
  columnInnerWidth: number,
): boolean {
  if (columnInnerWidth <= 0) return false;
  return metrics.every((m) => estimateMetricValueWidth(m.display_value || '', fontSize) <= columnInnerWidth);
}

function pickSharedValueFont(
  metrics: SocialStructuredMetric[],
  columnInnerWidth: number,
  preferred: number,
  minFont: number,
): { fontSize: number; singleLine: boolean } {
  let fs = preferred;
  while (fs >= minFont) {
    if (metricValuesFitSingleLine(metrics, fs, columnInnerWidth)) {
      return { fontSize: fs, singleLine: true };
    }
    fs -= 1;
  }
  return { fontSize: minFont, singleLine: metricValuesFitSingleLine(metrics, minFont, columnInnerWidth) };
}

function horizontalMetricGeometry(
  groupWidth: number,
  groupHeight: number,
  count: number,
  density: MetricGroupDensity,
): { gutter: number; columnWidth: number; padX: number; preferredValue: number; minValue: number; preferredLabel: number } {
  const n = Math.max(1, count);
  const gutter = density === 'compact' ? Math.max(6, Math.round(groupWidth * 0.012)) : Math.max(12, Math.round(groupWidth * 0.018));
  const padX = density === 'compact' ? 4 : 8;
  const columnWidth = Math.max(8, Math.floor((groupWidth - gutter * Math.max(0, n - 1)) / n));
  const heightRatio = density === 'compact' ? 0.32 : 0.38;
  const preferredValue = Math.max(density === 'compact' ? 16 : 18, Math.round(groupHeight * heightRatio));
  const minValue = Math.max(13, Math.round(preferredValue * 0.65));
  const preferredLabel = Math.max(10, Math.round(groupHeight * (density === 'compact' ? 0.14 : 0.16)));
  return { gutter, columnWidth, padX, preferredValue, minValue, preferredLabel };
}

/**
 * Sibling-aware metric group typography + layout fallback.
 * Prefers single-line values with equal columns; falls back
 * horizontal → compact horizontal → cards → stacked.
 */
export function fitMetricGroupPresentation(
  metrics: SocialStructuredMetric[],
  opts: {
    groupWidth: number;
    groupHeight: number;
    requestedLayout?: SocialMetricLayout | null;
    canvasW?: number;
    /** When true, never leave the requested layout family (still may compact density). */
    lockLayout?: boolean;
  },
): MetricGroupPresentation {
  const list = Array.isArray(metrics) ? metrics.slice(0, 3) : [];
  const n = Math.max(1, list.length);
  const groupW = Math.max(40, Math.round(finiteNum(opts.groupWidth, 400)));
  const groupH = Math.max(48, Math.round(finiteNum(opts.groupHeight, 120)));
  const requested =
    opts.requestedLayout === 'stacked' || opts.requestedLayout === 'cards' || opts.requestedLayout === 'horizontal'
      ? opts.requestedLayout
      : 'horizontal';
  const lock = Boolean(opts.lockLayout);

  const buildHorizontal = (density: MetricGroupDensity, requireSingleLine: boolean): MetricGroupPresentation | null => {
    const geo = horizontalMetricGeometry(groupW, groupH, n, density);
    const inner = Math.max(8, geo.columnWidth - geo.padX * 2);
    const valueFit = pickSharedValueFont(list, inner, geo.preferredValue, geo.minValue);
    if (requireSingleLine && !valueFit.singleLine) return null;
    const labelFont = Math.min(
      geo.preferredLabel,
      Math.max(9, Math.round(valueFit.fontSize * 0.42)),
    );
    return {
      layout: 'horizontal',
      density,
      valueFontSize: valueFit.fontSize,
      labelFontSize: labelFont,
      gutter: geo.gutter,
      columnWidth: geo.columnWidth,
      valueRowHeight: Math.round(valueFit.fontSize * 1.15),
      labelRowMinHeight: Math.round(labelFont * 1.25 * 2),
      valuesSingleLine: valueFit.singleLine,
      columnCount: n,
    };
  };

  if (requested === 'stacked') {
    const valueFont = Math.max(18, Math.round(groupH * (0.28 / Math.max(1, n / 2))));
    const labelFont = Math.max(10, Math.round(valueFont * 0.42));
    return {
      layout: 'stacked',
      density: 'comfortable',
      valueFontSize: valueFont,
      labelFontSize: labelFont,
      gutter: 8,
      columnWidth: groupW,
      valueRowHeight: Math.round(valueFont * 1.15),
      labelRowMinHeight: Math.round(labelFont * 1.25),
      valuesSingleLine: true,
      columnCount: 1,
    };
  }

  if (requested === 'cards') {
    const geo = horizontalMetricGeometry(groupW, groupH, n, 'comfortable');
    const inner = Math.max(8, geo.columnWidth - 24);
    const valueFit = pickSharedValueFont(list, inner, geo.preferredValue, geo.minValue);
    const labelFont = Math.max(9, Math.round(valueFit.fontSize * 0.4));
    return {
      layout: 'cards',
      density: 'comfortable',
      valueFontSize: valueFit.fontSize,
      labelFontSize: labelFont,
      gutter: geo.gutter,
      columnWidth: geo.columnWidth,
      valueRowHeight: Math.round(valueFit.fontSize * 1.15),
      labelRowMinHeight: Math.round(labelFont * 1.25 * 2),
      valuesSingleLine: valueFit.singleLine,
      columnCount: n,
    };
  }

  // requested === horizontal: comfortable → compact → (cards|stacked unless locked)
  const comfortable = buildHorizontal('comfortable', true);
  if (comfortable) return comfortable;
  const compact = buildHorizontal('compact', true);
  if (compact) return compact;
  if (lock) {
    return (
      buildHorizontal('compact', false) ||
      buildHorizontal('comfortable', false) || {
        layout: 'horizontal',
        density: 'compact',
        valueFontSize: 14,
        labelFontSize: 10,
        gutter: 6,
        columnWidth: Math.floor(groupW / n),
        valueRowHeight: 16,
        labelRowMinHeight: 24,
        valuesSingleLine: false,
        columnCount: n,
      }
    );
  }

  if (n >= 3) {
    const geo = horizontalMetricGeometry(groupW, groupH, n, 'compact');
    const inner = Math.max(8, geo.columnWidth - 20);
    const valueFit = pickSharedValueFont(list, inner, geo.preferredValue, Math.max(12, geo.minValue - 2));
    const labelFont = Math.max(9, Math.round(valueFit.fontSize * 0.4));
    return {
      layout: 'cards',
      density: 'compact',
      valueFontSize: valueFit.fontSize,
      labelFontSize: labelFont,
      gutter: geo.gutter,
      columnWidth: geo.columnWidth,
      valueRowHeight: Math.round(valueFit.fontSize * 1.15),
      labelRowMinHeight: Math.round(labelFont * 1.25 * 2),
      valuesSingleLine: valueFit.singleLine,
      columnCount: n,
    };
  }

  const valueFont = Math.max(16, Math.round(groupH * 0.28));
  const labelFont = Math.max(10, Math.round(valueFont * 0.42));
  return {
    layout: 'stacked',
    density: 'compact',
    valueFontSize: valueFont,
    labelFontSize: labelFont,
    gutter: 8,
    columnWidth: groupW,
    valueRowHeight: Math.round(valueFont * 1.15),
    labelRowMinHeight: Math.round(labelFont * 1.25),
    valuesSingleLine: true,
    columnCount: 1,
  };
}

/** Recompute METRIC_GROUP height for the chosen presentation (keeps group as one component). */
export function measureMetricGroupHeight(
  presentation: MetricGroupPresentation,
  metrics: SocialStructuredMetric[],
): number {
  const n = Math.max(1, metrics.length);
  if (presentation.layout === 'stacked') {
    return Math.max(
      48 * n,
      n * (presentation.valueRowHeight + presentation.labelRowMinHeight + presentation.gutter),
    );
  }
  const labelLinesBudget = 2;
  const padY = presentation.layout === 'cards' ? 20 : 8;
  return Math.max(
    72,
    padY +
      presentation.valueRowHeight +
      4 +
      Math.round(presentation.labelFontSize * 1.25 * labelLinesBudget) +
      padY,
  );
}

export function layoutMetricGroupElement(
  el: SocialMetricGroupElement,
  canvasW: number,
  canvasH: number,
  opts?: { allowLayoutFallback?: boolean },
): SocialMetricGroupElement {
  const geo = constrainElement(el, canvasW, canvasH);
  const allowFallback = opts?.allowLayoutFallback !== false;
  const requested: SocialMetricLayout =
    el.layout === 'stacked' || el.layout === 'cards' || el.layout === 'horizontal'
      ? el.layout
      : 'horizontal';
  const presentation = fitMetricGroupPresentation(el.metrics, {
    groupWidth: geo.width,
    groupHeight: Math.max(geo.height, 96),
    requestedLayout: requested,
    canvasW,
    lockLayout: requested === 'horizontal' ? !allowFallback : true,
  });
  const nextLayout: SocialMetricLayout =
    requested === 'horizontal' && allowFallback ? presentation.layout : requested;
  const height = Math.min(
    Math.max(geo.height, measureMetricGroupHeight(presentation, el.metrics)),
    Math.round(canvasH * 0.28),
  );
  return {
    ...el,
    ...constrainElement({ ...el, ...geo, height }, canvasW, canvasH),
    layout: nextLayout,
  };
}

/**
 * Grow a TEXT box to fit content at the current width (manual type / resize / AI copy).
 * Does not grow width. Shrinks font only when canvas safe bounds prevent further height growth.
 */
export function growTextBoxToContent(
  el: SocialTextElement,
  canvasW: number,
  canvasH: number,
  opts?: { minHeight?: number; allowShrinkFont?: boolean },
): SocialTextElement {
  const box = safeContentBox(canvasW, canvasH);
  const bold = isBoldishWeight(el.fontWeight) || el.role === 'headline';
  const prefs = roleFontPrefs(el.role === 'headline' || el.role === 'body' ? el.role : 'custom', canvasW);
  let font = clampInt(el.fontSize, 8, 200, 24);
  const width = clampInt(el.width, 8, box.width, Math.min(box.width, Math.max(8, el.width)));
  const x = clampInt(el.x, box.x, box.x + box.width, el.x);
  const y = clampInt(el.y, box.y, box.y + box.height, el.y);
  const minLine = Math.max(8, Math.round(font * LINE_HEIGHT));
  const maxH = Math.max(minLine, box.y + box.height - y);
  const minH = Math.max(minLine, opts?.minHeight ?? 0);

  const measure = (fs: number) => measureTextBlock(el.content || '', fs, width, bold);

  let measured = measure(font);
  let height = Math.max(minH, measured.height || minLine);

  if (height > maxH) {
    height = maxH;
    if (opts?.allowShrinkFont !== false) {
      while (font > prefs.min) {
        const m = measure(font);
        if (m.height <= maxH) {
          measured = m;
          height = Math.max(minLine, m.height);
          break;
        }
        font -= 2;
      }
      font = Math.max(prefs.min, font);
      measured = measure(font);
      height = Math.min(maxH, Math.max(Math.round(font * LINE_HEIGHT), measured.height, minH));
    }
  }

  const geo = constrainElement(
    { type: 'TEXT', x, y, width, height: Math.max(8, height) },
    canvasW,
    canvasH,
  );
  return { ...el, ...geo, fontSize: font };
}

function roleFontPrefs(role: string, canvasW: number) {
  const specs: Record<string, { preferredRatio: number; min: number; max: number }> = {
    headline: { preferredRatio: 0.062, min: 22, max: 84 },
    body: { preferredRatio: 0.024, min: 14, max: 28 },
    eyebrow: { preferredRatio: 0.015, min: 11, max: 18 },
    custom: { preferredRatio: 0.028, min: 14, max: 40 },
  };
  const spec = specs[role] ?? specs.custom!;
  return {
    preferred: Math.max(spec.min, Math.round(canvasW * spec.preferredRatio)),
    min: spec.min,
    max: spec.max,
  };
}

export function autoLayoutText(
  el: SocialTextElement,
  canvasW: number,
  canvasH: number,
  opts?: {
    preferredFont?: number;
    maxLines?: number;
    allowGrowWidth?: boolean;
    allowGrowHeight?: boolean;
    maxWidth?: number;
    maxHeight?: number;
  },
): SocialTextElement {
  const role = el.role === 'headline' || el.role === 'body' ? el.role : 'custom';
  const prefs = roleFontPrefs(role, canvasW);
  const box = safeContentBox(canvasW, canvasH);
  const bold = isBoldishWeight(el.fontWeight) || role === 'headline';
  const content = el.content || '';
  const breakLines = Math.max(1, explicitLineCount(content) || 1);
  const hasHardBreaks = /\r?\n/.test(content);
  const maxLines = Math.max(
    breakLines,
    opts?.maxLines ??
      (role === 'headline'
        ? hasHardBreaks || content.length > 28
          ? Math.max(3, breakLines)
          : 1
        : 6),
  );
  let font = clampInt(
    opts?.preferredFont ?? el.fontSize,
    prefs.min,
    prefs.max,
    prefs.preferred,
  );
  let x = clampInt(el.x, box.x, box.x + box.width, box.x);
  let y = clampInt(el.y, box.y, box.y + box.height, box.y);
  let width = clampInt(el.width, 40, box.width, Math.min(box.width, Math.max(200, box.width)));
  const widthCap = opts?.maxWidth != null ? Math.min(box.width, opts.maxWidth) : box.width;
  const heightCap =
    opts?.maxHeight != null
      ? Math.max(Math.round(font * LINE_HEIGHT), opts.maxHeight)
      : Math.max(Math.round(font * LINE_HEIGHT), box.y + box.height - y);

  const tryFit = (fs: number, w: number) => {
    const m = measureTextBlock(content, fs, w, bold);
    const ok = m.lines <= maxLines && m.height <= heightCap && (maxLines > 1 || m.lines <= 1);
    return { ...m, ok };
  };

  let height = Math.round(font * LINE_HEIGHT);
  let fit = tryFit(font, width);
  if (fit.ok) {
    height = Math.max(fit.height, Math.round(font * LINE_HEIGHT));
  } else {
    if (opts?.allowGrowWidth !== false) {
      const targetW = Math.min(
        widthCap,
        Math.max(width, fit.contentWidth + Math.round(font * 0.5), Math.round(box.width * 0.92)),
      );
      let growW = width;
      while (growW < targetW) {
        growW = Math.min(targetW, growW + Math.max(24, Math.floor(width / 6)));
        fit = tryFit(font, growW);
        if (fit.ok) {
          width = growW;
          height = Math.max(fit.height, Math.round(font * LINE_HEIGHT));
          if (el.align === 'center') {
            x = box.x + Math.max(0, Math.floor((box.width - width) / 2));
          } else {
            x = Math.max(box.x, Math.min(x, box.x + box.width - width));
          }
          break;
        }
      }
      if (!fit.ok && maxLines === 1) {
        width = widthCap;
        if (el.align === 'center') {
          x = box.x + Math.max(0, Math.floor((box.width - width) / 2));
        }
      }
    }

    if (!fit.ok && maxLines > 1) {
      width = Math.min(widthCap, Math.max(width, box.width));
      if (el.align === 'center') {
        x = box.x + Math.max(0, Math.floor((box.width - width) / 2));
      }
      fit = tryFit(font, width);
      if (fit.ok) {
        height = Math.min(heightCap, Math.max(fit.height, Math.round(font * LINE_HEIGHT)));
      }
    }

    if (!fit.ok) {
      while (font >= prefs.min) {
        fit = tryFit(font, width);
        if (fit.ok) break;
        font -= 2;
      }
      font = Math.max(prefs.min, font);
      fit = tryFit(font, width);
      height = Math.min(heightCap, Math.max(fit.height, Math.round(font * LINE_HEIGHT)));
    }
  }

  const geo = constrainElement(
    { type: 'TEXT', x, y, width, height: Math.max(8, height) },
    canvasW,
    canvasH,
  );
  return {
    ...el,
    ...geo,
    fontSize: font,
    role,
    fontWeight: role === 'headline' ? 'bold' : el.fontWeight,
  };
}

function boxesOverlap(a: SocialElement, b: SocialElement, gap: number): boolean {
  const ax2 = a.x + a.width;
  const ay2 = a.y + a.height;
  const bx2 = b.x + b.width;
  const by2 = b.y + b.height;
  return !(ax2 + gap <= b.x || bx2 + gap <= a.x || ay2 + gap <= b.y || by2 + gap <= a.y);
}

function priority(el: SocialElement): number {
  if (el.type === 'BUTTON') return 60;
  if (el.type === 'METRIC_GROUP') return 85;
  if (el.type === 'IMAGE') return 40;
  if (el.type === 'TEXT' && el.role === 'headline') return 100;
  if (el.type === 'TEXT' && el.role === 'body') return 80;
  return 70;
}

export function resolveCollisions(
  elements: SocialElement[],
  canvasW: number,
  canvasH: number,
): SocialElement[] {
  const box = safeContentBox(canvasW, canvasH);
  const gap = Math.max(12, Math.round(canvasH * 0.015));
  const next = elements.map((e) => ({ ...e }));

  const headline = next.find((e): e is SocialTextElement => e.type === 'TEXT' && e.role === 'headline');
  const body = next.find((e): e is SocialTextElement => e.type === 'TEXT' && e.role === 'body');
  const cta = next.find((e) => e.type === 'BUTTON');
  const metricGroup = next.find((e): e is SocialMetricGroupElement => e.type === 'METRIC_GROUP');

  if (headline && body) {
    const minBodyY = headline.y + headline.height + gap;
    if (body.y < minBodyY) {
      body.y = minBodyY;
      const maxBottom = cta ? cta.y - gap : box.y + box.height;
      const fitted = autoLayoutText(body, canvasW, canvasH, {
        preferredFont: body.fontSize,
        maxHeight: Math.max(Math.round(body.fontSize * LINE_HEIGHT), maxBottom - body.y),
        maxWidth: body.width,
      });
      Object.assign(body, fitted);
    }
  }

  if (body && cta) {
    let minCtaY = body.y + body.height + gap;
    const maxCtaY = box.y + box.height - cta.height;
    let targetY = Math.max(cta.y, minCtaY);
    if (targetY > maxCtaY) {
      const overflow = targetY - maxCtaY;
      body.y = Math.max(box.y, body.y - overflow);
      if (headline) {
        const minBody = headline.y + headline.height + gap;
        if (body.y < minBody) body.y = minBody;
      }
      Object.assign(
        body,
        autoLayoutText(body, canvasW, canvasH, {
          preferredFont: body.fontSize,
          maxHeight: Math.max(24, maxCtaY - gap - body.y),
        }),
      );
      minCtaY = body.y + body.height + gap;
      targetY = Math.min(Math.max(minCtaY, cta.y), maxCtaY);
    }
    cta.y = targetY;
    Object.assign(cta, constrainElement(cta, canvasW, canvasH));
  }

  if (headline && cta && !body && !metricGroup) {
    const minCtaY = headline.y + headline.height + gap;
    cta.y = Math.min(Math.max(cta.y, minCtaY), box.y + box.height - cta.height);
    Object.assign(cta, constrainElement(cta, canvasW, canvasH));
  }

  if (headline && metricGroup) {
    const minMgY = headline.y + headline.height + gap;
    if (metricGroup.y < minMgY) {
      metricGroup.y = minMgY;
      Object.assign(metricGroup, constrainElement(metricGroup, canvasW, canvasH));
    }
  }

  if (metricGroup && cta) {
    const minCtaY = metricGroup.y + metricGroup.height + gap;
    const maxCtaY = box.y + box.height - cta.height;
    cta.y = Math.min(Math.max(cta.y, minCtaY), maxCtaY);
    Object.assign(cta, constrainElement(cta, canvasW, canvasH));
  }

  const ordered = [...next].sort((a, b) => priority(b) - priority(a));
  for (let i = 0; i < ordered.length; i++) {
    const hi = ordered[i]!;
    for (let j = i + 1; j < ordered.length; j++) {
      const lo = ordered[j]!;
      if (!boxesOverlap(hi, lo, gap)) continue;
      if (priority(hi) < priority(lo)) continue;
      const newY = hi.y + hi.height + gap;
      const maxY = box.y + box.height - lo.height;
      lo.y = newY <= maxY ? newY : Math.max(box.y, maxY);
      Object.assign(lo, constrainElement(lo, canvasW, canvasH));
    }
  }

  return next.map((el) => ({ ...el, ...constrainElement(el, canvasW, canvasH) }));
}

export function alignElementConstrained(
  el: SocialElement,
  mode: AlignMode,
  canvasW: number,
  canvasH: number,
): SocialElement {
  const box = safeContentBox(canvasW, canvasH);
  const geo = constrainElement(el, canvasW, canvasH);
  let next: SocialElement = { ...el, ...geo };
  const m = mode === 'hcenter' ? 'center' : mode;

  if (m === 'left') {
    next = { ...next, x: next.type === 'TEXT' ? box.x : 0 };
    if (next.type === 'TEXT') next = { ...next, align: 'left' };
  } else if (m === 'right') {
    next = {
      ...next,
      x: next.type === 'TEXT' ? box.x + box.width - next.width : Math.max(0, canvasW - next.width),
    };
    if (next.type === 'TEXT') next = { ...next, align: 'right' };
  } else if (m === 'center') {
    next = { ...next, x: box.x + Math.max(0, Math.floor((box.width - next.width) / 2)) };
    if (next.type === 'TEXT') next = { ...next, align: 'center' };
  } else if (m === 'top') {
    next = {
      ...next,
      y: next.type === 'IMAGE' ? 0 : box.y,
    };
  } else if (m === 'middle' || m === 'vcenter') {
    next = { ...next, y: box.y + Math.max(0, Math.floor((box.height - next.height) / 2)) };
  } else if (m === 'bottom') {
    next = {
      ...next,
      y:
        next.type === 'IMAGE'
          ? Math.max(0, canvasH - next.height)
          : box.y + Math.max(0, box.height - next.height),
    };
  } else if (m === 'safe-area') {
    next = {
      ...next,
      x: box.x + Math.max(0, Math.floor((box.width - next.width) / 2)),
      y: Math.max(box.y, Math.min(next.y, box.y + box.height - next.height)),
    };
    if (next.type === 'TEXT') next = { ...next, align: 'center' };
  }

  return { ...next, ...constrainElement(next, canvasW, canvasH) };
}

export function resolveLayout(
  elements: SocialElement[],
  canvasW: number,
  canvasH: number,
  opts?: { refitText?: boolean },
): SocialElement[] {
  const refit = opts?.refitText !== false;
  const mapped = elements.map((el) => {
    if (el.type === 'TEXT' && refit) {
      return autoLayoutText(el, canvasW, canvasH, { preferredFont: el.fontSize });
    }
    if (el.type === 'METRIC_GROUP') {
      return layoutMetricGroupElement(el, canvasW, canvasH);
    }
    return { ...el, ...constrainElement(el, canvasW, canvasH) };
  });
  return resolveCollisions(mapped, canvasW, canvasH);
}

export function reflowElementsForFormat(
  elements: SocialElement[],
  canvasW: number,
  canvasH: number,
): SocialElement[] {
  const box = safeContentBox(canvasW, canvasH);
  const gap = Math.max(12, Math.round(canvasH * 0.015));
  const headlineSize = Math.max(22, Math.round(canvasW * 0.055));
  const bodySize = Math.max(14, Math.round(canvasW * 0.028));
  const ctaH = Math.max(36, Math.round(canvasH * 0.045));
  const ctaW = Math.min(box.width, Math.max(160, Math.round(canvasW * 0.38)));

  const next = elements.map((el) => {
    if (el.type === 'TEXT' && el.role === 'headline') {
      return autoLayoutText(
        {
          ...el,
          x: box.x,
          y: Math.round(canvasH * 0.22),
          width: box.width,
          fontSize: el.fontSize || headlineSize,
        },
        canvasW,
        canvasH,
        { preferredFont: el.fontSize || headlineSize, maxWidth: box.width },
      );
    }
    if (el.type === 'TEXT' && el.role === 'body') {
      return autoLayoutText(
        {
          ...el,
          x: box.x,
          y: Math.round(canvasH * 0.46),
          width: box.width,
          fontSize: el.fontSize || bodySize,
        },
        canvasW,
        canvasH,
        { preferredFont: el.fontSize || bodySize, maxWidth: box.width },
      );
    }
    if (el.type === 'BUTTON') {
      return {
        ...el,
        ...constrainElement(
          {
            ...el,
            width: Math.min(el.width || ctaW, ctaW),
            height: el.height || ctaH,
            x: Math.round((canvasW - Math.min(el.width || ctaW, ctaW)) / 2),
            y: Math.min(box.y + box.height - (el.height || ctaH), Math.round(canvasH * 0.88)),
          },
          canvasW,
          canvasH,
        ),
      };
    }
    if (el.type === 'METRIC_GROUP') {
      return layoutMetricGroupElement(
        {
          ...el,
          x: box.x,
          y: Math.round(canvasH * 0.46),
          width: box.width,
        },
        canvasW,
        canvasH,
      );
    }
    return { ...el, ...constrainElement(el, canvasW, canvasH) };
  });

  // Ensure vertical stack after format change
  const h = next.find((e): e is SocialTextElement => e.type === 'TEXT' && e.role === 'headline');
  const b = next.find((e): e is SocialTextElement => e.type === 'TEXT' && e.role === 'body');
  const mg = next.find((e): e is SocialMetricGroupElement => e.type === 'METRIC_GROUP');
  if (h && b && b.y < h.y + h.height + gap) {
    b.y = h.y + h.height + gap;
  }
  if (h && mg && mg.y < h.y + h.height + gap) {
    mg.y = h.y + h.height + gap;
  }
  return resolveCollisions(next, canvasW, canvasH);
}

/** Sanitize a patch so resize/move never writes NaN / non-finite geometry. */
export function sanitizeGeometryPatch(
  patch: Partial<SocialElement>,
): Partial<SocialElement> {
  const out: Partial<SocialElement> = { ...patch };
  if ('x' in out) (out as { x: number }).x = Math.round(finiteNum(out.x, 0));
  if ('y' in out) (out as { y: number }).y = Math.round(finiteNum(out.y, 0));
  if ('width' in out) {
    (out as { width: number }).width = Math.max(8, Math.round(finiteNum(out.width, 100)));
  }
  if ('height' in out) {
    (out as { height: number }).height = Math.max(8, Math.round(finiteNum(out.height, 40)));
  }
  if ('fontSize' in out) {
    (out as { fontSize: number }).fontSize = Math.max(
      8,
      Math.min(200, Math.round(finiteNum((out as { fontSize?: number }).fontSize, 24))),
    );
  }
  if ('zIndex' in out) {
    (out as { zIndex: number }).zIndex = Math.round(finiteNum(out.zIndex, 1));
  }
  return out;
}

export function applyElementPatch(
  el: SocialElement,
  patch: Partial<SocialElement>,
  canvasW: number,
  canvasH: number,
  opts?: { refitText?: boolean; resolveAll?: SocialElement[] },
): { element: SocialElement; elements?: SocialElement[] } {
  const clean = sanitizeGeometryPatch(patch);
  let next = { ...el, ...clean } as SocialElement;
  next = { ...next, ...constrainElement(next, canvasW, canvasH) };

  if (
    next.type === 'TEXT' &&
    (opts?.refitText ||
      'fontSize' in clean ||
      'content' in clean ||
      ('width' in clean && Boolean(opts?.resolveAll)))
  ) {
    // Content / font / width changes share one path: keep width, grow height to measured lines.
    // Full autoLayoutText (may grow width / shrink font) is reserved for format reflow + AI grammar.
    if ('width' in clean) {
      next.width = Math.max(8, finiteNum(clean.width, next.width));
    }
    next = growTextBoxToContent(next, canvasW, canvasH, {
      minHeight: 'height' in clean ? Math.max(8, finiteNum(clean.height, next.height)) : undefined,
    });
  }

  if (next.type === 'METRIC_GROUP' && ('width' in clean || 'height' in clean || 'layout' in clean || 'metrics' in clean)) {
    next = layoutMetricGroupElement(next, canvasW, canvasH, {
      allowLayoutFallback: next.layout === 'horizontal',
    });
  }

  if (opts?.resolveAll) {
    const replaced = opts.resolveAll.map((e) => (e.id === next.id ? next : e));
    return { element: next, elements: resolveCollisions(replaced, canvasW, canvasH) };
  }
  return { element: next };
}
