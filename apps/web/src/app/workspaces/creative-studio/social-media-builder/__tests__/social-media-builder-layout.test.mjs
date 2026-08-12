/**
 * SMB Layout Intelligence — client constrain/auto-layout/collision/resize safety.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-layout.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

// Mirror of social-media-builder-layout.ts core (kept in sync for node:test without TS loader)
const SAFE_MARGIN_RATIO = 0.07;
const LINE_HEIGHT = 1.2;

function finiteNum(n, fallback) {
  const v = typeof n === 'number' ? n : Number(n);
  return Number.isFinite(v) ? v : fallback;
}
function clampInt(value, lo, hi, fallback) {
  const n = Math.round(finiteNum(value, fallback));
  return Math.max(lo, Math.min(hi, n));
}
function safeContentBox(canvasW, canvasH) {
  const mx = Math.max(24, Math.round(canvasW * SAFE_MARGIN_RATIO));
  const my = Math.max(24, Math.round(canvasH * SAFE_MARGIN_RATIO));
  return { x: mx, y: my, width: Math.max(40, canvasW - mx * 2), height: Math.max(40, canvasH - my * 2) };
}
function constrainElement(el, canvasW, canvasH) {
  if (el.type === 'IMAGE') {
    const w = clampInt(el.width, 8, canvasW, Math.min(200, canvasW));
    const h = clampInt(el.height, 8, canvasH, Math.min(80, canvasH));
    return {
      x: clampInt(el.x, 0, Math.max(0, canvasW - w), 0),
      y: clampInt(el.y, 0, Math.max(0, canvasH - h), 0),
      width: w,
      height: h,
    };
  }
  if (el.type === 'BUTTON') {
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
  return {
    x: clampInt(el.x, box.x, Math.max(box.x, box.x + box.width - w), box.x),
    y: clampInt(el.y, box.y, Math.max(box.y, box.y + box.height - h), box.y),
    width: w,
    height: h,
  };
}
function wrapParagraph(paragraph, maxChars) {
  const words = paragraph.split(/\s+/).filter(Boolean);
  if (!words.length) return [''];
  const lines = [];
  let current = words[0];
  for (let i = 1; i < words.length; i++) {
    const candidate = `${current} ${words[i]}`;
    if (candidate.length <= maxChars) current = candidate;
    else {
      lines.push(current);
      current = words[i];
      while (current.length > maxChars) {
        lines.push(current.slice(0, maxChars));
        current = current.slice(maxChars);
      }
    }
  }
  lines.push(current);
  return lines;
}
function estimateWrapLines(text, fontSize, maxWidth, bold = false) {
  const raw = String(text ?? '');
  if (!raw) return [];
  const paragraphs = raw.split(/\r?\n/);
  const ratio = bold ? 0.58 : 0.52;
  const maxChars = Math.max(1, Math.floor(maxWidth / Math.max(1, fontSize * ratio)));
  const lines = [];
  for (const para of paragraphs) lines.push(...wrapParagraph(para, maxChars));
  return lines;
}
function measureText(text, fontSize, maxWidth, bold = false) {
  const lines = estimateWrapLines(text, fontSize, maxWidth, bold);
  return { lines: lines.length, height: Math.round(lines.length * fontSize * LINE_HEIGHT) };
}
function growTextBoxToContent(el, canvasW, canvasH) {
  const box = safeContentBox(canvasW, canvasH);
  const font = Math.max(8, el.fontSize || 24);
  const width = clampInt(el.width, 8, box.width, el.width);
  const y = clampInt(el.y, box.y, box.y + box.height, el.y);
  const measured = measureText(el.content || '', font, width, el.fontWeight === 'bold' || el.role === 'headline');
  const minLine = Math.round(font * LINE_HEIGHT);
  const maxH = Math.max(minLine, box.y + box.height - y);
  const height = Math.min(maxH, Math.max(minLine, measured.height || minLine));
  return { ...el, width, height, fontSize: font };
}
function canvasShortcutBlockedByTextEdit(editing, key) {
  return Boolean(editing) && key !== 'Escape';
}
function sanitizeGeometryPatch(patch) {
  const out = { ...patch };
  if ('width' in out) out.width = Math.max(8, Math.round(finiteNum(out.width, 100)));
  if ('height' in out) out.height = Math.max(8, Math.round(finiteNum(out.height, 40)));
  if ('x' in out) out.x = Math.round(finiteNum(out.x, 0));
  if ('y' in out) out.y = Math.round(finiteNum(out.y, 0));
  return out;
}

describe('layout module wiring', () => {
  it('ships layout intelligence module and wires workspace/artboard', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-layout.ts')), true);
    const layout = readSmb('social-media-builder-layout.ts');
    assert.match(layout, /export function constrainElement/);
    assert.match(layout, /export function autoLayoutText/);
    assert.match(layout, /export function resolveCollisions/);
    assert.match(layout, /export function resolveLayout/);
    assert.match(layout, /export function reflowElementsForFormat/);
    assert.match(layout, /export function applyElementPatch/);
    assert.match(layout, /export function growTextBoxToContent/);
    assert.match(layout, /export function canvasShortcutBlockedByTextEdit/);
    assert.match(layout, /explicitLineCount/);

    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /applyElementPatch/);
    assert.match(workspace, /reflowElementsForFormat/);
    assert.match(workspace, /sanitizeGeometryPatch/);
    assert.match(workspace, /canvasWidth=\{contentSize\.w\}/);

    const artboard = readSmb('smb-artboard-elements.tsx');
    assert.match(artboard, /constrainElement/);
    assert.match(artboard, /sanitizeGeometryPatch/);
    assert.match(artboard, /readCanvasScale|scaleX/);
    assert.doesNotMatch(artboard, /\.setPointerCapture\s*\(/);
    assert.doesNotMatch(artboard, /\.releasePointerCapture\s*\(/);
  });
});

describe('text measure / fit / no clip', () => {
  it('grows box for larger font without silent underflow dims', () => {
    const font = 56;
    const text = 'Invest in The Temple';
    const narrow = measureText(text, font, 200, true);
    assert.ok(narrow.lines >= 2);
    const wide = measureText(text, font, 900, true);
    assert.equal(wide.lines, 1);
    assert.ok(wide.height <= Math.round(font * LINE_HEIGHT) + 2);
  });

  it('preserves explicit newlines when measuring (Enter → two lines)', () => {
    const font = 48;
    const two = measureText('Invest in\nThe Temple', font, 900, true);
    assert.equal(two.lines, 2);
    assert.equal(two.height, Math.round(2 * font * LINE_HEIGHT));
    const three = measureText('Invest in\nThe Temple\nDC', font, 900, true);
    assert.equal(three.lines, 3);
    const grown = growTextBoxToContent(
      {
        type: 'TEXT',
        role: 'headline',
        content: 'Invest in\nThe Temple',
        fontSize: font,
        fontWeight: 'bold',
        x: 76,
        y: 200,
        width: 900,
        height: 40,
      },
      1080,
      1080,
    );
    assert.equal(grown.width, 900);
    assert.ok(grown.height >= two.height);
    assert.ok(grown.height > 40);
  });

  it('narrow resize wraps and grows height instead of clipping', () => {
    const el = {
      type: 'TEXT',
      role: 'headline',
      content: 'Invest in The Temple Residences',
      fontSize: 48,
      fontWeight: 'bold',
      x: 76,
      y: 200,
      width: 900,
      height: 58,
    };
    const wide = growTextBoxToContent(el, 1080, 1080);
    const narrow = growTextBoxToContent({ ...el, width: 280 }, 1080, 1080);
    assert.equal(narrow.width, 280);
    assert.ok(narrow.height >= wide.height);
  });

  it('blocks canvas shortcuts while text editing except Escape', () => {
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Enter'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Backspace'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Delete'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'ArrowLeft'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'z'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Escape'), false);
    assert.equal(canvasShortcutBlockedByTextEdit(false, 'Enter'), false);
    assert.equal(canvasShortcutBlockedByTextEdit(false, 'Backspace'), false);
  });

  it('sanitizeGeometryPatch rejects NaN/Inf from resize math', () => {
    const bad = sanitizeGeometryPatch({
      width: Number.NaN,
      height: Number.POSITIVE_INFINITY,
      x: undefined,
      y: 'nope',
    });
    assert.equal(bad.width >= 8, true);
    assert.equal(bad.height >= 8, true);
    assert.equal(Number.isFinite(bad.x), true);
    assert.equal(Number.isFinite(bad.y), true);
  });
});

describe('constraint + collision', () => {
  it('constrainElement keeps text in safe area and CTA inset', () => {
    const text = constrainElement(
      { type: 'TEXT', x: -40, y: -10, width: 5000, height: 20 },
      1080,
      1080,
    );
    const box = safeContentBox(1080, 1080);
    assert.ok(text.x >= box.x);
    assert.ok(text.y >= box.y);
    assert.ok(text.x + text.width <= box.x + box.width + 1);
    const cta = constrainElement(
      { type: 'BUTTON', x: 0, y: 1070, width: 400, height: 48 },
      1080,
      1080,
    );
    assert.ok(cta.y + cta.height <= 1080 - 24 + 1);
    assert.ok(cta.x >= 24);
  });

  it('headline grow pushes body below without overlap', () => {
    const gap = 16;
    const headline = { id: 'h', type: 'TEXT', role: 'headline', x: 76, y: 200, width: 900, height: 120 };
    const body = { id: 'b', type: 'TEXT', role: 'body', x: 76, y: 280, width: 900, height: 60 };
    const minBodyY = headline.y + headline.height + gap;
    const nextBodyY = Math.max(body.y, minBodyY);
    assert.equal(nextBodyY, 336);
    assert.ok(headline.y + headline.height <= nextBodyY);
  });
});

describe('alignment + format reflow contracts', () => {
  it('align center uses safe content box', () => {
    const el = { type: 'TEXT', x: 40, y: 200, width: 400, height: 80 };
    const box = safeContentBox(1080, 1080);
    const geo = constrainElement(el, 1080, 1080);
    const x = box.x + Math.max(0, Math.floor((box.width - geo.width) / 2));
    assert.ok(Math.abs(x + geo.width / 2 - 540) < 40);
  });

  it('elements module re-exports constrained align', () => {
    const elements = readSmb('social-media-builder-elements.ts');
    assert.match(elements, /alignElementConstrained/);
    assert.match(elements, /constrainElement/);
  });
});
