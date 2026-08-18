/**
 * Selected-layer typography / transform controls + AI move preserving styles.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-layer-controls.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const messagesDir = join(smbDir, '../../../../../messages');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

function readMessages(name) {
  return readFileSync(join(messagesDir, name), 'utf8');
}

function clampFontSize(value, fallback = 24) {
  const n = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(n)) return fallback;
  return Math.max(8, Math.min(200, Math.round(n)));
}

function nudgeFontSize(current, delta) {
  return clampFontSize(current + delta, current);
}

function parseSocialFontWeight(raw) {
  if (raw === 'medium' || raw === 'semibold' || raw === 'bold' || raw === 'normal') return raw;
  return 'normal';
}

function parseElement(raw) {
  if (!raw || typeof raw !== 'object') return null;
  if (raw.type === 'TEXT') {
    return {
      id: raw.id,
      type: 'TEXT',
      x: raw.x,
      y: raw.y,
      width: raw.width,
      height: raw.height,
      zIndex: raw.zIndex,
      content: raw.content ?? '',
      fontSize: raw.fontSize ?? 24,
      fontWeight: parseSocialFontWeight(raw.fontWeight),
      align: raw.align === 'left' || raw.align === 'right' ? raw.align : 'center',
      color: raw.color ?? '#fff',
      role: raw.role ?? 'custom',
      ...(raw.fontFamily ? { fontFamily: raw.fontFamily } : {}),
      ...(raw.lineHeight !== undefined ? { lineHeight: raw.lineHeight } : {}),
      ...(raw.letterSpacing !== undefined ? { letterSpacing: raw.letterSpacing } : {}),
      ...(raw.opacity !== undefined ? { opacity: raw.opacity } : {}),
    };
  }
  return null;
}

function serializeElement(el) {
  return {
    id: el.id,
    type: el.type,
    x: el.x,
    y: el.y,
    width: el.width,
    height: el.height,
    zIndex: el.zIndex,
    content: el.content,
    fontSize: el.fontSize,
    fontWeight: el.fontWeight,
    align: el.align,
    color: el.color,
    role: el.role,
    ...(el.fontFamily ? { fontFamily: el.fontFamily } : {}),
    ...(el.lineHeight !== undefined ? { lineHeight: el.lineHeight } : {}),
    ...(el.letterSpacing !== undefined ? { letterSpacing: el.letterSpacing } : {}),
    ...(el.opacity !== undefined ? { opacity: el.opacity } : {}),
  };
}

const MOVE_HEADLINE_DOWN_RE =
  /ba[sş]l[iı][gğ][iı].{0,24}a[sş]a[gğ][iı]|move (the )?headline down|headline.{0,12}down/i;

function applyMoveHeadlineDown(elements, canvasH) {
  const target = elements.find((el) => el.type === 'TEXT' && el.role === 'headline');
  if (!target) return null;
  const delta = Math.max(18, Math.round(canvasH * 0.04));
  return elements.map((el) => {
    if (el.id !== target.id || el.type !== 'TEXT') return el;
    const y = Math.min(canvasH - el.height - 8, el.y + delta);
    return { ...el, y };
  });
}

describe('font size stepper / type-in', () => {
  it('decrements and increments by 2 and accepts typed values', () => {
    assert.equal(nudgeFontSize(42, -2), 40);
    assert.equal(nudgeFontSize(40, 2), 42);
    assert.equal(clampFontSize('36'), 36);
    assert.equal(clampFontSize(7), 8);
    assert.equal(clampFontSize(999), 200);
  });
});

describe('style drawer wiring', () => {
  it('exposes contextual controls for text, logo, image, and CTA', () => {
    const drawer = readSmb('social-media-builder-rail-drawers.tsx');
    assert.match(drawer, /data-testid="smb-style-font-size-stepper"/);
    assert.match(drawer, /data-testid="smb-style-font-size-dec"/);
    assert.match(drawer, /data-testid="smb-style-font-size-inc"/);
    assert.match(drawer, /data-testid="smb-style-font-family"/);
    assert.match(drawer, /data-testid="smb-style-font-weight"/);
    assert.match(drawer, /data-testid="smb-style-align"/);
    assert.match(drawer, /data-testid="smb-style-text-color"/);
    assert.match(drawer, /data-testid="smb-style-line-height"/);
    assert.match(drawer, /data-testid="smb-style-letter-spacing"/);
    assert.match(drawer, /data-testid="smb-style-opacity"/);
    assert.match(drawer, /data-testid="smb-style-lock-aspect"/);
    assert.match(drawer, /data-testid="smb-style-object-fit"/);
    assert.match(drawer, /data-testid="smb-style-border-radius"/);
    assert.match(drawer, /data-testid="smb-style-padding"/);
    assert.match(drawer, /nudgeFontSize/);
    assert.match(drawer, /role === 'logo'/);
  });

  it('opens the style rail when a layer is selected', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /setSelectedElementId\(elementId\);\s*setRightRailId\('style'\)/s);
  });

  it('pins compact typography controls on selection chrome and the bottom dock', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    const drawer = readSmb('social-media-builder-rail-drawers.tsx');
    assert.match(drawer, /export function SmbLayerStyleBar/);
    assert.match(drawer, /data-testid=\{tid\('font-size-stepper'\)\}/);
    assert.match(workspace, /smb-ws__selection-chrome/);
    assert.match(workspace, /testIdPrefix="smb-live-style"/);
    assert.match(workspace, /testIdPrefix="smb-dock-style"/);
    assert.match(workspace, /<SmbLayerStyleBar/);
  });

  it('keeps the live style bar on selectedElementId after mouseup, not pointer-down-only', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /!previewMode && selectedElementId && selectedElement/);
    assert.match(workspace, /handleArtboardBackgroundPointerDown/);
    assert.match(workspace, /onPointerDown=\{handleArtboardBackgroundPointerDown\}/);
    assert.doesNotMatch(workspace, /suppressArtboardDeselectRef/);
    assert.doesNotMatch(workspace, /handleArtboardBackgroundClick/);
    assert.doesNotMatch(workspace, /isPointerDown/);
    assert.doesNotMatch(workspace, /selectedElementId && isDragging/);
  });

  it('ships i18n keys for layer style controls', () => {
    const en = readMessages('en.json');
    const tr = readMessages('tr.json');
    for (const src of [en, tr]) {
      assert.match(src, /"fontFamily"/);
      assert.match(src, /"lineHeight"/);
      assert.match(src, /"letterSpacing"/);
      assert.match(src, /"selectLayerHint"/);
      assert.match(src, /"medium"/);
      assert.match(src, /"semibold"/);
      assert.match(src, /"lockAspect"/);
    }
  });
});

describe('persistence roundtrip for typography fields', () => {
  it('keeps fontSize, weight, color, align, and optional style fields', () => {
    const el = {
      id: 'text-headline',
      type: 'TEXT',
      role: 'headline',
      content: 'The Temple',
      fontSize: 36,
      fontWeight: 'semibold',
      align: 'left',
      color: '#f5c542',
      fontFamily: 'serif',
      lineHeight: 1.35,
      letterSpacing: 1.5,
      opacity: 0.9,
      x: 80,
      y: 400,
      width: 800,
      height: 80,
      zIndex: 5,
    };
    const loaded = parseElement(serializeElement(el));
    assert.equal(loaded.fontSize, 36);
    assert.equal(loaded.fontWeight, 'semibold');
    assert.equal(loaded.align, 'left');
    assert.equal(loaded.color, '#f5c542');
    assert.equal(loaded.fontFamily, 'serif');
    assert.equal(loaded.lineHeight, 1.35);
    assert.equal(loaded.letterSpacing, 1.5);
    assert.equal(loaded.opacity, 0.9);
  });

  it('persistence module serializes the new optional style fields', () => {
    const src = readSmb('social-media-builder-persistence.ts');
    assert.match(src, /fontFamily/);
    assert.match(src, /lineHeight/);
    assert.match(src, /letterSpacing/);
    assert.match(src, /lockAspectRatio/);
    assert.match(src, /borderRadius/);
    assert.match(src, /parseSocialFontWeight/);
  });
});

describe('AI move headline preserves manual fontSize', () => {
  it('matches Başlığı biraz aşağı al', () => {
    assert.equal(MOVE_HEADLINE_DOWN_RE.test('Başlığı biraz aşağı al'), true);
    assert.equal(MOVE_HEADLINE_DOWN_RE.test('move headline down'), true);
  });

  it('only patches y and keeps fontSize / weight / color', () => {
    const elements = [
      {
        id: 'text-headline',
        type: 'TEXT',
        role: 'headline',
        content: 'The Temple',
        fontSize: 36,
        fontWeight: 'medium',
        align: 'left',
        color: '#ffcc00',
        x: 80,
        y: 500,
        width: 800,
        height: 80,
        zIndex: 5,
      },
    ];
    const next = applyMoveHeadlineDown(elements, 1080);
    assert.ok(next);
    assert.equal(next[0].fontSize, 36);
    assert.equal(next[0].fontWeight, 'medium');
    assert.equal(next[0].color, '#ffcc00');
    assert.equal(next[0].align, 'left');
    assert.ok(next[0].y > 500);
  });

  it('documents move_headline_down as a y-only mapper command', () => {
    const src = readSmb('social-media-builder-ai-edit.ts');
    assert.match(src, /move_headline_down/);
    assert.match(src, /applyMoveHeadlineDown/);
    assert.match(src, /Position-only patch|preserves fontSize|y-only/i);
  });
});
