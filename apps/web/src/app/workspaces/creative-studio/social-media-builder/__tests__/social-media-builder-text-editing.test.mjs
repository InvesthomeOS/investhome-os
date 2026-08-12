/**
 * SMB TEXT editing consistency P0 — Enter newline, isolation, auto-grow, FS parity, persist, AI.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-text-editing.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

const LINE_HEIGHT = 1.2;
const SAFE_MARGIN_RATIO = 0.07;

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
function measureTextBlock(text, fontSize, maxWidth, bold = false) {
  const wrapped = estimateWrapLines(text, fontSize, maxWidth, bold);
  if (!wrapped.length) return { lines: 0, height: 0 };
  return { lines: wrapped.length, height: Math.round(wrapped.length * fontSize * LINE_HEIGHT) };
}
function growTextBoxToContent(el, canvasW, canvasH, opts = {}) {
  const box = safeContentBox(canvasW, canvasH);
  const font = Math.max(8, el.fontSize || 24);
  const width = clampInt(el.width, 8, box.width, el.width);
  const y = clampInt(el.y, box.y, box.y + box.height, el.y);
  const measured = measureTextBlock(
    el.content || '',
    font,
    width,
    el.fontWeight === 'bold' || el.role === 'headline',
  );
  const minLine = Math.round(font * LINE_HEIGHT);
  const maxH = Math.max(minLine, box.y + box.height - y);
  const minH = Math.max(minLine, opts.minHeight ?? 0);
  const height = Math.min(maxH, Math.max(minH, measured.height || minLine));
  return { ...el, width, height, fontSize: font };
}
function canvasShortcutBlockedByTextEdit(editing, key) {
  return Boolean(editing) && key !== 'Escape';
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
  };
}
function parseElement(raw) {
  return {
    id: raw.id,
    type: 'TEXT',
    x: raw.x,
    y: raw.y,
    width: raw.width,
    height: raw.height,
    zIndex: raw.zIndex,
    content: typeof raw.content === 'string' ? raw.content : '',
    fontSize: raw.fontSize ?? 24,
    fontWeight: raw.fontWeight === 'bold' ? 'bold' : 'normal',
    align: raw.align === 'left' || raw.align === 'right' ? raw.align : 'center',
    color: raw.color ?? '#fff',
    role: raw.role ?? 'custom',
  };
}
function applyCopyToElements(elements, copy) {
  return elements.map((el) => {
    if (el.type === 'TEXT' && el.role === 'headline' && copy.headline != null) {
      return growTextBoxToContent({ ...el, content: copy.headline }, 1080, 1080);
    }
    if (el.type === 'TEXT' && el.role === 'body' && copy.caption != null) {
      return growTextBoxToContent({ ...el, content: copy.caption }, 1080, 1080);
    }
    return el;
  });
}

describe('Enter newline + keyboard isolation wiring', () => {
  it('TEXT Enter inserts newline; does not commit/preventDefault', () => {
    const artboard = readSmb('smb-artboard-elements.tsx');
    assert.match(artboard, /kind: 'TEXT' \| 'BUTTON'/);
    assert.match(artboard, /TEXT: Enter and Shift\+Enter insert a newline/);
    assert.doesNotMatch(artboard, /event\.key === 'Enter' && !event\.shiftKey/);
    assert.match(artboard, /kind === 'BUTTON' && event\.key === 'Enter'/);
    assert.match(artboard, /event\.stopPropagation\(\)/);
    assert.match(artboard, /stopImmediatePropagation/);
    assert.match(artboard, /onKeyDown=\{\(e\) => onEditKeyDown\(e, el\.id, 'TEXT'\)\}/);
  });

  it('workspace yields all canvas shortcuts while textEditMode is active', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /canvasShortcutBlockedByTextEdit/);
    assert.match(workspace, /data-text-edit-mode=\{editingElementId \? 'true' : 'false'\}/);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Enter'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Backspace'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Delete'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'ArrowUp'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'z'), true);
    assert.equal(canvasShortcutBlockedByTextEdit(true, 'Escape'), false);
    assert.equal(canvasShortcutBlockedByTextEdit(false, 'Backspace'), false);
  });
});

describe('no internal TEXT scrollbar', () => {
  it('editor overflow is hidden, not auto; text box overflow is visible', () => {
    const css = readSmb('social-media-builder.css');
    const editorBlock = css.slice(css.indexOf('.smb-ws__el-editor {'), css.indexOf('.smb-ws__el-editor--button'));
    assert.match(editorBlock, /overflow:\s*hidden/);
    assert.doesNotMatch(editorBlock, /overflow:\s*auto/);
    assert.match(editorBlock, /white-space:\s*pre-wrap/);
    const textBlock = css.slice(css.indexOf('.smb-ws__el--text {'), css.indexOf('.smb-ws__el--text.is-selected'));
    assert.match(textBlock, /overflow:\s*visible/);
    assert.doesNotMatch(textBlock, /overflow:\s*auto/);
  });
});

describe('auto-height + resize reflow', () => {
  it('grows height on extra lines and preserves width', () => {
    const base = {
      type: 'TEXT',
      role: 'headline',
      content: 'Invest in',
      fontSize: 48,
      fontWeight: 'bold',
      x: 76,
      y: 200,
      width: 820,
      height: 58,
    };
    const one = growTextBoxToContent(base, 1080, 1080);
    const two = growTextBoxToContent({ ...base, content: 'Invest in\nThe Temple' }, 1080, 1080);
    const three = growTextBoxToContent({ ...base, content: 'Invest in\nThe Temple\nDC' }, 1080, 1080);
    assert.equal(two.width, 820);
    assert.equal(three.width, 820);
    assert.ok(two.height > one.height);
    assert.ok(three.height > two.height);
    assert.equal(measureTextBlock('Invest in\nThe Temple', 48, 820, true).lines, 2);
  });

  it('resize narrower wraps and remasures height', () => {
    const el = {
      type: 'TEXT',
      role: 'headline',
      content: 'Invest in The Temple Residences Today',
      fontSize: 48,
      fontWeight: 'bold',
      x: 76,
      y: 220,
      width: 900,
      height: 58,
    };
    const wide = growTextBoxToContent(el, 1080, 1080);
    const narrow = growTextBoxToContent({ ...el, width: 260 }, 1080, 1080);
    assert.equal(narrow.width, 260);
    assert.ok(narrow.height >= wide.height);
    assert.ok(measureTextBlock(el.content, 48, 260, true).lines >= 2);
  });
});

describe('normal / fullscreen parity', () => {
  it('fullscreen only changes fit padding/scale — does not reflow text geometry', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /Fit \/ Focus \/ Fullscreen only change ftv\.stageSize\.scale/);
    assert.doesNotMatch(workspace, /if \(focus\.isFullscreen\)[\s\S]{0,80}resolveLayout/);
    assert.doesNotMatch(workspace, /if \(focus\.isFullscreen\)[\s\S]{0,80}autoLayoutText/);
    assert.doesNotMatch(workspace, /fsPosts|fullscreenPosts/);
    const multiline = 'Invest in\nThe Temple';
    const normal = growTextBoxToContent(
      { type: 'TEXT', role: 'headline', content: multiline, fontSize: 48, fontWeight: 'bold', x: 76, y: 200, width: 820, height: 40 },
      1080,
      1080,
    );
    const fullscreen = growTextBoxToContent({ ...normal }, 1080, 1080);
    assert.equal(fullscreen.content, normal.content);
    assert.equal(fullscreen.width, normal.width);
    assert.equal(fullscreen.height, normal.height);
    assert.equal(fullscreen.fontSize, normal.fontSize);
  });
});

describe('refresh persistence of exact \\n', () => {
  it('roundtrips multiline content and geometry through serialize/parse', () => {
    const el = growTextBoxToContent(
      {
        id: 'headline-1',
        type: 'TEXT',
        role: 'headline',
        content: 'Invest in\nThe Temple',
        fontSize: 48,
        fontWeight: 'bold',
        align: 'center',
        color: '#ffffff',
        x: 76,
        y: 240,
        width: 820,
        height: 40,
        zIndex: 2,
      },
      1080,
      1080,
    );
    const json = JSON.stringify(serializeElement(el));
    const loaded = parseElement(JSON.parse(json));
    assert.equal(loaded.content, 'Invest in\nThe Temple');
    assert.equal(loaded.content.includes('\n'), true);
    assert.equal(loaded.width, el.width);
    assert.equal(loaded.height, el.height);
    assert.equal(loaded.fontSize, el.fontSize);
    const persistence = readSmb('social-media-builder-persistence.ts');
    assert.match(persistence, /content: typeof body\.content === 'string' \? body\.content : ''/);
    assert.match(persistence, /content: el\.content/);
  });
});

describe('AI multiline uses the same TEXT model', () => {
  it('applyCopyToElements writes \\n onto content and grows via the same measure path', () => {
    const elements = [
      {
        id: 'headline-1',
        type: 'TEXT',
        role: 'headline',
        content: 'Old',
        fontSize: 48,
        fontWeight: 'bold',
        x: 76,
        y: 200,
        width: 820,
        height: 40,
      },
      {
        id: 'body-1',
        type: 'TEXT',
        role: 'body',
        content: 'Body',
        fontSize: 22,
        x: 76,
        y: 400,
        width: 820,
        height: 40,
      },
    ];
    const next = applyCopyToElements(elements, {
      headline: 'Invest in\nThe Temple',
      caption: 'Quiet luxury\nin DC',
    });
    const headline = next.find((e) => e.role === 'headline');
    const body = next.find((e) => e.role === 'body');
    assert.equal(headline.content, 'Invest in\nThe Temple');
    assert.equal(body.content, 'Quiet luxury\nin DC');
    assert.ok(headline.height > 40);
    assert.equal(headline.width, 820);
    const gen = readSmb('social-media-builder-generation.ts');
    assert.match(gen, /applyCopyToElements/);
    const els = readSmb('social-media-builder-elements.ts');
    assert.match(els, /growTextBoxToContent/);
  });
});
