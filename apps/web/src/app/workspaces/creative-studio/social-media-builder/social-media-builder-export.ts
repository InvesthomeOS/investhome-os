/**
 * Social Media Builder post export — PNG of CURRENT persistent post elements.
 * Uses authenticated blob/display URLs only (never taints with third-party CDN).
 */

import {
  sortElementsByZ,
  type SocialElement,
} from './social-media-builder-elements';

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

async function drawElement(
  ctx: CanvasRenderingContext2D,
  el: SocialElement,
  imageUrlsByAssetId: Record<string, string>,
) {
  if (el.type === 'TEXT') {
    ctx.fillStyle = el.color;
    ctx.textAlign = el.align;
    ctx.textBaseline = 'top';
    const weight = el.fontWeight === 'bold' ? 700 : 400;
    ctx.font = `${weight} ${el.fontSize}px system-ui, sans-serif`;
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
    roundRect(ctx, el.x, el.y, el.width, el.height, el.height / 2);
    ctx.fill();
    ctx.fillStyle = el.textColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    const fontSize = Math.max(12, Math.round(el.height * 0.42));
    ctx.font = `600 ${fontSize}px system-ui, sans-serif`;
    ctx.fillText(el.label || '', el.x + el.width / 2, el.y + el.height / 2);
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
 * Renders the current persistent post (cover + elements) to a PNG and downloads it.
 */
export async function exportSocialPostPng(input: SocialPostExportInput): Promise<void> {
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
