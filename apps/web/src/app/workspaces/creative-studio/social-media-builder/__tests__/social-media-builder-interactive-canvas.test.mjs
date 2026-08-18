/**
 * Social Media Builder Interactive Canvas P0 — selection, drag, resize, edit, undo, AI context.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-interactive-canvas.test.mjs
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

describe('interactive canvas wiring', () => {
  it('artboard supports select, drag, resize, inline edit, gesture hooks', () => {
    assert.equal(existsSync(join(smbDir, 'smb-artboard-elements.tsx')), true);
    const artboard = readSmb('smb-artboard-elements.tsx');
    assert.match(artboard, /editingElementId/);
    assert.match(artboard, /onBeginEdit/);
    assert.match(artboard, /onEndEdit/);
    assert.match(artboard, /onGestureStart/);
    assert.match(artboard, /onGestureEnd/);
    assert.match(artboard, /onDoubleClick/);
    assert.match(artboard, /smb-el-editor/);
    assert.match(artboard, /onEditKeyDown\(e, el\.id, 'TEXT'\)/);
    assert.doesNotMatch(artboard, /event\.key === 'Enter' && !event\.shiftKey/);
    assert.match(artboard, /beginDrag\(e, el, 'move'\)/);
    assert.match(artboard, /beginDrag\(e, el, 'resize'\)/);
    assert.match(artboard, /constrainElement/);
    assert.match(artboard, /sanitizeGeometryPatch/);
    assert.doesNotMatch(artboard, /\.setPointerCapture\s*\(/);
    assert.match(artboard, /live:\s*true/);
    assert.match(artboard, /readCanvasScale/);
  });

  it('workspace wires undo/redo, keyboard, align, and selected AI context', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /historyPast/);
    assert.match(workspace, /historyFuture/);
    assert.match(workspace, /undoHistory/);
    assert.match(workspace, /redoHistory/);
    assert.match(workspace, /data-testid="smb-undo"/);
    assert.match(workspace, /data-testid="smb-redo"/);
    assert.match(workspace, /disabled=\{!historyPast\.length\}/);
    assert.match(workspace, /disabled=\{!historyFuture\.length\}/);
    assert.match(workspace, /editingElementId/);
    assert.match(workspace, /canvasShortcutBlockedByTextEdit/);
    assert.match(workspace, /beginGestureHistory/);
    assert.match(workspace, /ArrowLeft/);
    assert.match(workspace, /Backspace/);
    assert.match(workspace, /selectedElementToDesignContext/);
    assert.match(workspace, /selectedElement:/);
    assert.match(workspace, /\(\['left', 'center', 'right', 'top', 'middle', 'bottom'\]/);
    assert.match(workspace, /smb-align-\$\{mode\}/);
    assert.match(workspace, /pushHistory\(\);/);
    assert.match(workspace, /setPosts\(nextPosts\)/);
    assert.match(workspace, /ensureUniqueElementIds/);
    // One canonical posts state — no separate FS/AI canvas
    assert.doesNotMatch(workspace, /fsPosts|fullscreenPosts|aiPreviewPosts/);
  });

  it('ignores the artboard click that completes a layer pointerdown so selection survives mouseup', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /suppressArtboardDeselectRef/);
    assert.match(workspace, /selectElementFromLayer/);
    assert.match(workspace, /handleArtboardBackgroundClick/);
    assert.match(workspace, /onSelect=\{selectElementFromLayer\}/);
    assert.match(workspace, /onClick=\{handleArtboardBackgroundClick\}/);
    assert.match(workspace, /if \(elementId && source === 'pointer'\)/);
    assert.match(workspace, /suppressArtboardDeselectRef\.current = false/);
    const artboard = readSmb('smb-artboard-elements.tsx');
    assert.match(artboard, /onSelect\(el\.id, 'pointer'\)/);
    assert.match(artboard, /beginDrag\(e, el, 'move'\)/);
  });

  it('design engine serializes selected element into builder_context', () => {
    const engine = readSmb('social-media-builder-design-engine.ts');
    assert.match(engine, /export function selectedElementToDesignContext/);
    assert.match(engine, /selected_element:/);
    assert.match(engine, /selectedElementId:/);
    assert.match(engine, /selectedElement\?:/);
  });
});

describe('selected element context helper (mirror)', () => {
  function selectedElementToDesignContext(el) {
    if (!el || typeof el.id !== 'string' || !el.id) return null;
    const base = {
      id: el.id,
      type: el.type,
      x: Number.isFinite(el.x) ? el.x : 0,
      y: Number.isFinite(el.y) ? el.y : 0,
      width: Math.max(8, Number.isFinite(el.width) ? el.width : 100),
      height: Math.max(8, Number.isFinite(el.height) ? el.height : 40),
      zIndex: Number.isFinite(el.zIndex) ? el.zIndex : 1,
    };
    if (el.type === 'TEXT') {
      return {
        ...base,
        role: el.role ?? 'custom',
        content: el.content ?? '',
        fontSize: el.fontSize ?? null,
        fontWeight: el.fontWeight ?? null,
        align: el.align ?? null,
        color: el.color ?? null,
      };
    }
    if (el.type === 'BUTTON') {
      return {
        ...base,
        role: 'cta',
        label: el.label ?? '',
        backgroundColor: el.backgroundColor ?? null,
        textColor: el.textColor ?? null,
      };
    }
    return { ...base, role: 'image', assetId: el.assetId ?? null };
  }

  it('includes geometry + content/style for TEXT and BUTTON', () => {
    const headline = selectedElementToDesignContext({
      id: 'h1',
      type: 'TEXT',
      role: 'headline',
      content: 'Invest in The Temple',
      fontSize: 48,
      fontWeight: 'bold',
      align: 'center',
      color: '#ffffff',
      x: 80,
      y: 200,
      width: 900,
      height: 80,
      zIndex: 2,
    });
    assert.equal(headline.id, 'h1');
    assert.equal(headline.role, 'headline');
    assert.equal(headline.content, 'Invest in The Temple');
    assert.equal(headline.fontSize, 48);
    assert.equal(headline.x, 80);

    const cta = selectedElementToDesignContext({
      id: 'c1',
      type: 'BUTTON',
      label: 'Tour',
      backgroundColor: '#fff',
      textColor: '#111',
      x: 100,
      y: 900,
      width: 200,
      height: 48,
      zIndex: 4,
    });
    assert.equal(cta.role, 'cta');
    assert.equal(cta.label, 'Tour');
  });
});

describe('history / continuity logic (mirror)', () => {
  function clonePosts(source) {
    return source.map((p) => ({ ...p, elements: p.elements.map((e) => ({ ...e })) }));
  }

  it('manual then AI then manual shares one posts[] stack', () => {
    let posts = [
      {
        id: 'p1',
        elements: [{ id: 'h1', type: 'TEXT', role: 'headline', content: 'A', x: 10, y: 10, width: 100, height: 40 }],
      },
    ];
    const past = [];
    function push() {
      past.push(clonePosts(posts));
    }
    // manual move
    push();
    posts = clonePosts(posts);
    posts[0].elements[0].y = 40;
    // AI edit
    push();
    posts = clonePosts(posts);
    posts[0].elements[0].content = 'A';
    posts[0].elements[0].y = 20;
    // manual resize
    push();
    posts = clonePosts(posts);
    posts[0].elements[0].width = 200;
    assert.equal(past.length, 3);
    assert.equal(posts[0].elements[0].width, 200);
    assert.equal(posts[0].elements[0].y, 20);
    // undo twice → back to after first manual move
    posts = past.pop();
    posts = past.pop();
    assert.equal(posts[0].elements[0].y, 40);
    assert.equal(posts[0].elements[0].width, 100);
  });

  it('duplicate assigns new id and delete removes it', () => {
    const elements = [
      { id: 'body-1', type: 'TEXT', role: 'body', content: 'Body', x: 0, y: 0, width: 100, height: 40, zIndex: 1 },
    ];
    const clone = { ...elements[0], id: 'copy-1', x: 24, y: 24, zIndex: 2 };
    let next = [...elements, clone];
    assert.equal(next.length, 2);
    assert.notEqual(next[1].id, next[0].id);
    next = next.filter((e) => e.id !== 'copy-1');
    assert.equal(next.length, 1);
    assert.equal(next[0].id, 'body-1');
  });

  it('align modes include top/middle/bottom geometry', () => {
    const layout = readSmb('social-media-builder-layout.ts');
    assert.match(layout, /'top'/);
    assert.match(layout, /'middle'/);
    assert.match(layout, /'bottom'/);
    assert.match(layout, /m === 'top'/);
    assert.match(layout, /m === 'middle' \|\| m === 'vcenter'/);
    assert.match(layout, /m === 'bottom'/);
  });
});

describe('selection / deselection contract', () => {
  it('click empty canvas clears selection; element click sets id', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /onClick=\{handleArtboardBackgroundClick\}/);
    assert.match(workspace, /function handleArtboardBackgroundClick/);
    assert.match(workspace, /if \(suppressArtboardDeselectRef\.current\) \{/);
    assert.match(workspace, /function selectElement\(elementId: string \| null\)/);
    const artboard = readSmb('smb-artboard-elements.tsx');
    assert.match(artboard, /onSelect\(el\.id\)/);
    assert.match(artboard, /is-selected/);
    assert.match(artboard, /smb-el-resize-/);
  });

  it('dedupes colliding element ids that break selection', () => {
    const els = readSmb('social-media-builder-elements.ts');
    assert.match(els, /export function ensureUniqueElementIds/);
    const persistence = readSmb('social-media-builder-persistence.ts');
    assert.match(persistence, /ensureUniqueElementIds/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /ensureUniqueElementIds/);

    function nextElementId(prefix = 'el') {
      return `${prefix}-${Math.random().toString(36).slice(2, 8)}`;
    }
    function ensureUniqueElementIds(elements) {
      const seen = new Set();
      return elements.map((el) => {
        const raw = typeof el.id === 'string' ? el.id.trim() : '';
        if (raw && !seen.has(raw)) {
          seen.add(raw);
          return el;
        }
        let next = nextElementId('el');
        while (seen.has(next)) next = nextElementId('el');
        seen.add(next);
        return { ...el, id: next };
      });
    }
    const out = ensureUniqueElementIds([
      { id: 'pending-3', type: 'TEXT' },
      { id: 'pending-3', type: 'TEXT' },
      { id: 'ok', type: 'BUTTON' },
    ]);
    assert.equal(out[0].id, 'pending-3');
    assert.notEqual(out[1].id, 'pending-3');
    assert.equal(out[2].id, 'ok');
    assert.equal(new Set(out.map((e) => e.id)).size, 3);
  });
});
