/**
 * Minimum Social Media Builder post export — canvas PNG with image + text.
 * Uses authenticated blob/display URLs only (never taints with third-party CDN).
 */

export type SocialPostExportInput = {
  width: number;
  height: number;
  imageUrl: string | null;
  headline: string;
  caption: string;
  cta: string;
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
  const words = text.trim().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const lines: string[] = [];
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
  return lines;
}

/**
 * Renders the current post to a PNG and triggers a browser download.
 * Throws on missing canvas support, image load failure, or empty blob.
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

  if (input.imageUrl) {
    const img = await loadImage(input.imageUrl);
    drawCover(ctx, img, width, height);
  } else {
    throw new Error('No image to export');
  }

  const gradient = ctx.createLinearGradient(0, height * 0.35, 0, height);
  gradient.addColorStop(0, 'rgba(0,0,0,0)');
  gradient.addColorStop(1, 'rgba(0,0,0,0.62)');
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

  const padX = width * 0.08;
  const maxText = width - padX * 2;
  let cursorY = height * 0.72;

  ctx.fillStyle = '#ffffff';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const headlineSize = Math.max(22, Math.round(width * 0.055));
  ctx.font = `700 ${headlineSize}px system-ui, sans-serif`;
  for (const line of wrapText(ctx, input.headline || '', maxText).slice(0, 3)) {
    ctx.fillText(line, width / 2, cursorY);
    cursorY += headlineSize * 1.15;
  }

  const captionSize = Math.max(14, Math.round(width * 0.028));
  ctx.font = `400 ${captionSize}px system-ui, sans-serif`;
  ctx.globalAlpha = 0.92;
  for (const line of wrapText(ctx, input.caption || '', maxText).slice(0, 3)) {
    ctx.fillText(line, width / 2, cursorY);
    cursorY += captionSize * 1.25;
  }
  ctx.globalAlpha = 1;

  if (input.cta) {
    cursorY += Math.round(height * 0.02);
    ctx.font = `600 ${captionSize}px system-ui, sans-serif`;
    const label = input.cta;
    const textW = ctx.measureText(label).width;
    const btnPadX = captionSize * 0.9;
    const btnPadY = captionSize * 0.45;
    const btnW = textW + btnPadX * 2;
    const btnH = captionSize + btnPadY * 2;
    const btnX = (width - btnW) / 2;
    ctx.fillStyle = '#ffffff';
    roundRect(ctx, btnX, cursorY, btnW, btnH, btnH / 2);
    ctx.fill();
    ctx.fillStyle = '#111827';
    ctx.textBaseline = 'middle';
    ctx.fillText(label, width / 2, cursorY + btnH / 2);
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
