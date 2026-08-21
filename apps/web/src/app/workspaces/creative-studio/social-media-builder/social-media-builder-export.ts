/**
 * Social Media Builder post export — PNG of CURRENT persistent post elements.
 * Uses authenticated blob/display URLs only (never taints with third-party CDN).
 */

import {
  socialFontFamilyCss,
  socialFontWeightCss,
  sortElementsByZ,
  type SocialElement,
} from './social-media-builder-elements';
import { fitMetricGroupPresentation } from './social-media-builder-layout';

export type SocialPostExportInput = {
  width: number;
  height: number;
  /** Background / cover display URL (authenticated blob). */
  coverImageUrl: string | null;
  elements: SocialElement[];
  /** assetId → authenticated display URL for IMAGE elements. */
  imageUrlsByAssetId?: Record<string, string>;
  brandLogo: boolean;
  filename: string;
};

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('Failed to load image for export'));
    img.src = src;
  });
}

function drawCover(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  width: number,
  height: number,
) {
  const scale = Math.max(width / img.naturalWidth, height / img.naturalHeight);
  const w = img.naturalWidth * scale;
  const h = img.naturalHeight * scale;
  const x = (width - w) / 2;
  const y = (height - h) / 2;
  ctx.drawImage(img, x, y, w, h);
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
): string[] {
  const paragraphs = String(text ?? '').split(/\r?\n/);
  const lines: string[] = [];
  for (const para of paragraphs) {
    const words = para.split(/\s+/).filter(Boolean);
    if (!words.length) {
      lines.push('');
      continue;
    }
    let current = words[0]!;
    for (let i = 1; i < words.length; i += 1) {
      const next = `${current} ${words[i]}`;
      if (ctx.measureText(next).width <= maxWidth) {
        current = next;
      } else {
        lines.push(current);
        current = words[i]!;
      }
    }
    lines.push(current);
  }
  return lines;
}

/** Best-effort CSS linear-gradient → canvas gradient for overlay fidelity. */
function parseCssLinearGradient(
  ctx: CanvasRenderingContext2D,
  css: string,
  x: number,
  y: number,
  w: number,
  h: number,
): CanvasGradient | null {
  const inner = css.slice(css.indexOf('(') + 1, css.lastIndexOf(')')).trim();
  if (!inner) return null;
  const toTop = /to\s+top/i.test(inner);
  const toBottom = /to\s+bottom/i.test(inner);
  const toRight = /to\s+right/i.test(inner);
  let grad: CanvasGradient;
  if (toRight) {
    grad = ctx.createLinearGradient(x, y, x + w, y);
  } else if (toTop) {
    grad = ctx.createLinearGradient(x, y + h, x, y);
  } else if (toBottom) {
    grad = ctx.createLinearGradient(x, y, x, y + h);
  } else {
    grad = ctx.createLinearGradient(x, y + h, x, y);
  }
  const stopRe =
    /(rgba?\([^)]+\)|transparent|#[0-9a-fA-F]{3,8})\s+(\d+(?:\.\d+)?)%/g;
  let match: RegExpExecArray | null;
  let count = 0;
  while ((match = stopRe.exec(inner)) !== null) {
    const color = match[1] === 'transparent' ? 'rgba(0,0,0,0)' : match[1];
    const pos = Math.max(0, Math.min(1, Number(match[2]) / 100));
    try {
      grad.addColorStop(pos, color);
      count += 1;
    } catch {
      /* ignore invalid stop */
    }
  }
  if (count === 0) return null;
  return grad;
}

async function drawElement(
  ctx: CanvasRenderingContext2D,
  el: SocialElement,
  imageUrlsByAssetId: Record<string, string>,
) {
  if (el.type === 'TEXT') {
    ctx.fillStyle = el.color;
    ctx.textAlign = el.align;
    ctx.textBaseline = 'top';
    const weight = socialFontWeightCss(el.fontWeight);
    const family = socialFontFamilyCss(el.fontFamily) || 'system-ui, sans-serif';
    ctx.font = `${weight} ${el.fontSize}px ${family}`;
    const anchorX =
      el.align === 'left'
        ? el.x
        : el.align === 'right'
          ? el.x + el.width
          : el.x + el.width / 2;
    let cursorY = el.y;
    for (const line of wrapText(ctx, el.content || '', el.width).slice(0, 8)) {
      ctx.fillText(line, anchorX, cursorY);
      cursorY += el.fontSize * 1.2;
      if (cursorY > el.y + el.height) break;
    }
    return;
  }

  if (el.type === 'BUTTON') {
    ctx.fillStyle = el.backgroundColor;
    roundRect(ctx, el.x, el.y, el.width, el.height, el.borderRadius ?? el.height / 2);
    ctx.fill();
    ctx.fillStyle = el.textColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const fontSize = Math.max(12, Math.round(el.fontSize ?? el.height * 0.42));
    const family = socialFontFamilyCss(el.fontFamily) || 'system-ui, sans-serif';
    ctx.font = `600 ${fontSize}px ${family}`;
    ctx.fillText(el.label || '', el.x + el.width / 2, el.y + el.height / 2);
    return;
  }

  if (el.type === 'SHAPE') {
    const fill = el.fill || '#C4A35A';
    const radius = el.borderRadius ?? 0;
    ctx.save();
    ctx.globalAlpha = typeof el.opacity === 'number' ? Math.max(0, Math.min(1, el.opacity)) : 1;
    if (typeof fill === 'string' && fill.includes('linear-gradient')) {
      const grad = parseCssLinearGradient(ctx, fill, el.x, el.y, el.width, el.height);
      if (grad) {
        ctx.fillStyle = grad;
      } else {
        ctx.fillStyle = 'rgba(8,6,4,0.45)';
      }
    } else {
      ctx.fillStyle = fill;
    }
    if (el.shapeKind === 'line' || (el.height <= 3 && el.width > el.height * 4)) {
      ctx.fillRect(el.x, el.y, el.width, Math.max(1, el.height));
    } else if (radius > 0) {
      roundRect(ctx, el.x, el.y, el.width, el.height, radius);
      ctx.fill();
    } else {
      ctx.fillRect(el.x, el.y, el.width, el.height);
    }
    ctx.restore();
    return;
  }

  if (el.type === 'METRIC_GROUP') {
    const metrics = Array.isArray(el.metrics) ? el.metrics : [];
    const n = Math.max(1, metrics.length);
    const requested = el.layout === 'stacked' || el.layout === 'cards' ? el.layout : 'horizontal';
    const presentation = fitMetricGroupPresentation(metrics, {
      groupWidth: el.width,
      groupHeight: el.height,
      requestedLayout: requested,
      lockLayout: true,
    });
    const layout = requested;
    ctx.fillStyle = el.color || '#ffffff';
    ctx.textBaseline = 'alphabetic';
    if (layout === 'stacked') {
      const rowH = el.height / n;
      metrics.forEach((metric, i) => {
        const y = el.y + i * rowH;
        ctx.textAlign = 'left';
        ctx.font = `700 ${presentation.valueFontSize}px system-ui, sans-serif`;
        ctx.fillText(metric.display_value || '', el.x, y + presentation.valueRowHeight * 0.85);
        ctx.font = `500 ${presentation.labelFontSize}px system-ui, sans-serif`;
        ctx.fillText(metric.label || '', el.x, y + presentation.valueRowHeight + presentation.labelFontSize * 1.2);
      });
      return;
    }
    const colW = presentation.columnWidth || el.width / n;
    metrics.forEach((metric, i) => {
      const x = el.x + i * (colW + presentation.gutter);
      if (layout === 'cards') {
        ctx.save();
        ctx.fillStyle = 'rgba(15, 23, 42, 0.28)';
        roundRect(ctx, x, el.y, colW, el.height, 10);
        ctx.fill();
        ctx.restore();
        ctx.fillStyle = el.color || '#ffffff';
      }
      const padX = layout === 'cards' ? 12 : 0;
      ctx.textAlign = 'left';
      ctx.font = `700 ${presentation.valueFontSize}px system-ui, sans-serif`;
      ctx.fillText(metric.display_value || '', x + padX, el.y + presentation.valueRowHeight * 0.85);
      ctx.font = `500 ${presentation.labelFontSize}px system-ui, sans-serif`;
      const labelY = el.y + presentation.valueRowHeight + 4 + presentation.labelFontSize;
      for (const line of wrapText(ctx, metric.label || '', colW - padX * 2).slice(0, 2)) {
        ctx.fillText(line, x + padX, labelY);
      }
    });
    return;
  }

  if (el.type === 'IMAGE' && el.assetId) {
    const url = imageUrlsByAssetId[el.assetId];
    if (!url) return;
    try {
      const img = await loadImage(url);
      const scale = Math.max(el.width / img.naturalWidth, el.height / img.naturalHeight);
      const w = img.naturalWidth * scale;
      const h = img.naturalHeight * scale;
      const x = el.x + (el.width - w) / 2;
      const y = el.y + (el.height - h) / 2;
      ctx.save();
      ctx.beginPath();
      ctx.rect(el.x, el.y, el.width, el.height);
      ctx.clip();
      ctx.drawImage(img, x, y, w, h);
      ctx.restore();
    } catch {
      /* skip failed image element */
    }
  }
}

/**
 * Renders the current persistent post (cover + elements) to a PNG blob.
 * Shared by local download and Canva transfer — does not change drawing.
 */
export async function renderSocialPostPng(input: SocialPostExportInput): Promise<Blob> {
  const width = Math.max(1, Math.round(input.width));
  const height = Math.max(1, Math.round(input.height));
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas unavailable');
  }

  ctx.fillStyle = '#1f2937';
  ctx.fillRect(0, 0, width, height);

  const hasCover = Boolean(input.coverImageUrl);
  const hasElements = input.elements.length > 0;
  if (!hasCover && !hasElements) {
    throw new Error('No image to export');
  }

  if (input.coverImageUrl) {
    const img = await loadImage(input.coverImageUrl);
    drawCover(ctx, img, width, height);
  }

  const gradient = ctx.createLinearGradient(0, 0, 0, height * 0.36);
  gradient.addColorStop(0, 'rgba(0,0,0,0.32)');
  gradient.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  if (input.brandLogo) {
    const badge = Math.max(28, Math.round(width * 0.06));
    ctx.fillStyle = 'rgba(255,255,255,0.92)';
    roundRect(ctx, width * 0.06, height * 0.06, badge * 1.6, badge, badge * 0.2);
    ctx.fill();
    ctx.fillStyle = '#111827';
    ctx.font = `600 ${Math.round(badge * 0.45)}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('IH', width * 0.06 + badge * 0.8, height * 0.06 + badge / 2);
  }

  const urls = input.imageUrlsByAssetId ?? {};
  for (const el of sortElementsByZ(input.elements)) {
    await drawElement(ctx, el, urls);
  }

  const blob = await new Promise<Blob | null>((resolve) => {
    canvas.toBlob((value) => resolve(value), 'image/png');
  });
  if (!blob) {
    throw new Error('Export failed');
  }
  return blob;
}

export type CanvaLayerElement = {
  id: string;
  type: 'TEXT' | 'IMAGE' | 'BUTTON' | 'METRIC_GROUP';
  role?: string;
  content?: string;
  label?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  zIndex: number;
  fontSize?: number;
  fontWeight?: 'normal' | 'bold';
  align?: 'left' | 'center' | 'right';
  color?: string;
  backgroundColor?: string;
  textColor?: string;
  asset_key?: string;
  layout?: string;
  metrics?: Array<{ display_value: string; label: string }>;
};

export type CanvaLayersPayload = {
  width: number;
  height: number;
  brand_logo: boolean;
  cover_asset_key: string | null;
  elements: CanvaLayerElement[];
};

export type CanvaLayerImagePlan = { filename: string; url: string };

function canvaAssetFilename(id: string, prefix: string): string {
  const safe = String(id || 'el')
    .replace(/[^A-Za-z0-9._-]+/g, '_')
    .slice(0, 48);
  return `${prefix}_${safe || 'el'}.png`;
}

/**
 * Maps SMB canvas layers to Canva Design Import payload (PPTX on the API).
 * Does not alter PNG rendering.
 */
export function buildCanvaLayersPayload(input: SocialPostExportInput): {
  layers: CanvaLayersPayload;
  imagePlan: CanvaLayerImagePlan[];
} {
  const imagePlan: CanvaLayerImagePlan[] = [];
  let coverKey: string | null = null;
  if (input.coverImageUrl) {
    coverKey = 'cover.png';
    imagePlan.push({ filename: coverKey, url: input.coverImageUrl });
  }

  const urls = input.imageUrlsByAssetId ?? {};
  const elements: CanvaLayerElement[] = sortElementsByZ(input.elements).map((el) => {
    if (el.type === 'TEXT') {
      return {
        id: el.id,
        type: 'TEXT',
        role: el.role,
        content: el.content,
        x: el.x,
        y: el.y,
        width: el.width,
        height: el.height,
        zIndex: el.zIndex,
        fontSize: el.fontSize,
        fontWeight: el.fontWeight,
        align: el.align,
        color: el.color,
      };
    }
    if (el.type === 'BUTTON') {
      return {
        id: el.id,
        type: 'BUTTON',
        label: el.label,
        x: el.x,
        y: el.y,
        width: el.width,
        height: el.height,
        zIndex: el.zIndex,
        backgroundColor: el.backgroundColor,
        textColor: el.textColor,
      };
    }
    if (el.type === 'SHAPE') {
      return {
        id: el.id,
        type: 'BUTTON',
        label: '',
        x: el.x,
        y: el.y,
        width: el.width,
        height: el.height,
        zIndex: el.zIndex,
        backgroundColor: el.fill,
        textColor: el.fill,
      };
    }
    if (el.type === 'METRIC_GROUP') {
      return {
        id: el.id,
        type: 'METRIC_GROUP',
        x: el.x,
        y: el.y,
        width: el.width,
        height: el.height,
        zIndex: el.zIndex,
        color: el.color,
        layout: el.layout,
        metrics: (el.metrics || []).map((metric) => ({
          display_value: metric.display_value,
          label: metric.label,
        })),
      };
    }
    const filename = el.assetId ? canvaAssetFilename(el.id, 'img') : undefined;
    if (filename && el.assetId && urls[el.assetId]) {
      imagePlan.push({ filename, url: urls[el.assetId]! });
    }
    return {
      id: el.id,
      type: 'IMAGE',
      role: el.role,
      x: el.x,
      y: el.y,
      width: el.width,
      height: el.height,
      zIndex: el.zIndex,
      asset_key: filename,
    };
  });

  return {
    layers: {
      width: Math.max(1, Math.round(input.width)),
      height: Math.max(1, Math.round(input.height)),
      brand_logo: Boolean(input.brandLogo),
      cover_asset_key: coverKey,
      elements,
    },
    imagePlan,
  };
}

export async function fetchCanvaLayerImages(
  plan: CanvaLayerImagePlan[],
): Promise<Array<{ filename: string; blob: Blob }>> {
  const out: Array<{ filename: string; blob: Blob }> = [];
  for (const item of plan) {
    try {
      const response = await fetch(item.url);
      if (!response.ok) continue;
      const blob = await response.blob();
      if (blob.size > 0) out.push({ filename: item.filename, blob });
    } catch {
      /* skip missing layer image — PNG fallback still applies */
    }
  }
  return out;
}

/**
 * Renders the current persistent post (cover + elements) to a PNG and downloads it.
 */
export async function exportSocialPostPng(input: SocialPostExportInput): Promise<void> {
  const blob = await renderSocialPostPng(input);

  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = input.filename.endsWith('.png')
      ? input.filename
      : `${input.filename}.png`;
    anchor.rel = 'noopener';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}
