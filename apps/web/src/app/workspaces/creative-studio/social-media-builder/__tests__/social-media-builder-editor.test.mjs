/**
 * Social Media Builder P0 post editor — schema, elements, persist, export wiring.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-editor.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const componentsDir = join(here, '../../_components');

// Pure logic mirrored in-test; React modules asserted via source wiring.

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

function readComponent(name) {
  return readFileSync(join(componentsDir, name), 'utf8');
}

const SAMPLE_UUID = '11111111-1111-4111-8111-111111111111';
const TEMPLE_UUID = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const OTHER_UUID = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isMediaAssetUuid(id) {
  return Boolean(id && UUID_RE.test(String(id).trim()));
}

function createDefaultElements(width, height, opts = {}) {
  return [
    {
      id: 'headline-1',
      type: 'TEXT',
      role: 'headline',
      content: opts.headline ?? 'Headline',
      fontSize: 48,
      fontWeight: 'bold',
      align: 'center',
      color: '#ffffff',
      x: 80,
      y: Math.round(height * 0.68),
      width: width - 160,
      height: 80,
      zIndex: 2,
    },
    {
      id: 'body-1',
      type: 'TEXT',
      role: 'body',
      content: opts.caption ?? 'Body',
      fontSize: 24,
      fontWeight: 'normal',
      align: 'center',
      color: '#ffffff',
      x: 80,
      y: Math.round(height * 0.78),
      width: width - 160,
      height: 60,
      zIndex: 3,
    },
    {
      id: 'cta-1',
      type: 'BUTTON',
      label: opts.cta ?? 'Schedule a private tour',
      backgroundColor: '#ffffff',
      textColor: '#111827',
      x: Math.round(width * 0.3),
      y: Math.round(height * 0.88),
      width: Math.round(width * 0.4),
      height: 48,
      zIndex: 4,
    },
  ];
}

function serializeElement(el) {
  if (el.type === 'TEXT') {
    return {
      id: el.id,
      type: 'TEXT',
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
  if (el.type === 'IMAGE') {
    return {
      id: el.id,
      type: 'IMAGE',
      x: el.x,
      y: el.y,
      width: el.width,
      height: el.height,
      zIndex: el.zIndex,
      assetId: el.assetId && isMediaAssetUuid(el.assetId) ? el.assetId : null,
    };
  }
  return {
    id: el.id,
    type: 'BUTTON',
    x: el.x,
    y: el.y,
    width: el.width,
    height: el.height,
    zIndex: el.zIndex,
    label: el.label,
    backgroundColor: el.backgroundColor,
    textColor: el.textColor,
  };
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
      fontWeight: raw.fontWeight === 'bold' ? 'bold' : 'normal',
      align: raw.align === 'left' || raw.align === 'right' ? raw.align : 'center',
      color: raw.color ?? '#fff',
      role: raw.role ?? 'custom',
    };
  }
  if (raw.type === 'IMAGE') {
    const assetId = raw.assetId || raw.asset_id || null;
    return {
      id: raw.id,
      type: 'IMAGE',
      x: raw.x,
      y: raw.y,
      width: raw.width,
      height: raw.height,
      zIndex: raw.zIndex,
      assetId: assetId && isMediaAssetUuid(assetId) ? assetId : null,
    };
  }
  if (raw.type === 'BUTTON' || raw.type === 'CTA') {
    return {
      id: raw.id,
      type: 'BUTTON',
      x: raw.x,
      y: raw.y,
      width: raw.width,
      height: raw.height,
      zIndex: raw.zIndex,
      label: raw.label ?? '',
      backgroundColor: raw.backgroundColor ?? '#fff',
      textColor: raw.textColor ?? '#111',
    };
  }
  return null;
}

function serializeSocialPost(post) {
  return {
    id: post.id,
    format: post.format,
    formatPreset: post.formatPreset,
    width: post.width,
    height: post.height,
    name: post.name,
    coverAssetId: post.coverAssetId,
    linked_project_id: post.linkedProjectId,
    elements: post.elements.map(serializeElement),
  };
}

function parseSocialPost(raw, linked = null) {
  if (!raw || typeof raw !== 'object') return null;
  const elements = Array.isArray(raw.elements)
    ? raw.elements.map(parseElement).filter(Boolean)
    : [];
  return {
    id: raw.id,
    formatPreset: raw.formatPreset || 'square',
    width: raw.width || 1080,
    height: raw.height || 1080,
    name: raw.name || 'Post',
    coverAssetId:
      raw.coverAssetId && isMediaAssetUuid(raw.coverAssetId) ? raw.coverAssetId : null,
    linkedProjectId: raw.linked_project_id || raw.linkedProjectId || linked,
    elements:
      elements.length > 0
        ? elements
        : createDefaultElements(raw.width || 1080, raw.height || 1080, {
            headline: raw.headline,
            caption: raw.caption,
          }),
  };
}

function hydrateSocialPostsFromDraft(input) {
  const parsed = Array.isArray(input.posts)
    ? input.posts.map((p) => parseSocialPost(p, input.linkedProjectId)).filter(Boolean)
    : [];
  if (parsed.length) {
    const withCover = parsed.map((p, i) => ({
      ...p,
      coverAssetId:
        p.coverAssetId ||
        (i === 0 && input.coverAssetId && isMediaAssetUuid(input.coverAssetId)
          ? input.coverAssetId
          : null),
      linkedProjectId: p.linkedProjectId || input.linkedProjectId || null,
    }));
    return {
      posts: withCover,
      selectedPostId: input.selectedPostId || withCover[0].id,
    };
  }
  const elements = createDefaultElements(1080, 1080, { headline: 'Migrated', caption: '' });
  const post = {
    id: 'p-migrated',
    formatPreset: 'square',
    width: 1080,
    height: 1080,
    name: 'Migrated',
    coverAssetId: input.coverAssetId && isMediaAssetUuid(input.coverAssetId) ? input.coverAssetId : null,
    linkedProjectId: input.linkedProjectId || null,
    elements,
  };
  return { posts: [post], selectedPostId: post.id };
}

function duplicateElement(el) {
  return { ...el, id: `${el.id}-copy`, x: el.x + 24, y: el.y + 24, zIndex: el.zIndex + 1 };
}

function applyCopyToElements(elements, copy) {
  return elements.map((el) => {
    if (el.type === 'TEXT' && el.role === 'headline' && copy.headline != null) {
      return { ...el, content: copy.headline };
    }
    if (el.type === 'TEXT' && el.role === 'body' && copy.caption != null) {
      return { ...el, content: copy.caption };
    }
    if (el.type === 'BUTTON' && copy.cta != null) {
      return { ...el, label: copy.cta };
    }
    return el;
  });
}

describe('P0 source modules', () => {
  it('ships element model, artboard binder, updated export/persistence', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-elements.ts')), true);
    assert.equal(existsSync(join(smbDir, 'smb-artboard-elements.tsx')), true);
    assert.match(readSmb('social-media-builder-elements.ts'), /type: 'TEXT'/);
    assert.match(readSmb('social-media-builder-elements.ts'), /type: 'IMAGE'/);
    assert.match(readSmb('social-media-builder-elements.ts'), /type: 'BUTTON'/);
    assert.match(readSmb('social-media-builder-persistence.ts'), /serializeSocialPost/);
    assert.match(readSmb('social-media-builder-persistence.ts'), /hydrateSocialPostsFromDraft/);
    assert.match(readSmb('social-media-builder-export.ts'), /elements/);
    assert.match(readSmb('social-media-builder-export.ts'), /coverImageUrl/);
  });
});

describe('schema migration + posts persist', () => {
  it('migrates coverImage-only draft into posts with default TEXT/BUTTON elements', () => {
    const hydrated = hydrateSocialPostsFromDraft({
      coverAssetId: SAMPLE_UUID,
      linkedProjectId: TEMPLE_UUID,
    });
    assert.equal(hydrated.posts.length, 1);
    assert.equal(hydrated.posts[0].coverAssetId, SAMPLE_UUID);
    assert.equal(hydrated.posts[0].linkedProjectId, TEMPLE_UUID);
    assert.ok(hydrated.posts[0].elements.some((e) => e.type === 'TEXT'));
    assert.ok(hydrated.posts[0].elements.some((e) => e.type === 'BUTTON'));
  });

  it('roundtrips text, CTA, Asset ID, and positions', () => {
    const elements = createDefaultElements(1080, 1080, {
      headline: 'Temple Launch',
      caption: 'DC luxury',
      cta: 'Book tour',
    });
    elements.push({
      id: 'img-1',
      type: 'IMAGE',
      assetId: SAMPLE_UUID,
      x: 100,
      y: 120,
      width: 400,
      height: 300,
      zIndex: 5,
    });
    const post = {
      id: 'p1',
      format: 'feed',
      formatPreset: 'square',
      width: 1080,
      height: 1080,
      name: 'Square',
      coverAssetId: SAMPLE_UUID,
      linkedProjectId: TEMPLE_UUID,
      elements,
    };
    const saved = serializeSocialPost(post);
    const loaded = parseSocialPost(saved, TEMPLE_UUID);
    assert.equal(loaded.coverAssetId, SAMPLE_UUID);
    assert.equal(loaded.linkedProjectId, TEMPLE_UUID);
    const headline = loaded.elements.find((e) => e.role === 'headline');
    const cta = loaded.elements.find((e) => e.type === 'BUTTON');
    const img = loaded.elements.find((e) => e.type === 'IMAGE');
    assert.equal(headline.content, 'Temple Launch');
    assert.equal(cta.label, 'Book tour');
    assert.equal(img.assetId, SAMPLE_UUID);
    assert.equal(img.x, 100);
    assert.equal(img.y, 120);
  });

  it('duplicate and delete preserve ids independently', () => {
    const el = createDefaultElements(1080, 1080)[0];
    const copy = duplicateElement(el);
    assert.notEqual(copy.id, el.id);
    assert.equal(copy.content, el.content);
    const remaining = [el, copy].filter((e) => e.id !== el.id);
    assert.equal(remaining.length, 1);
    assert.equal(remaining[0].id, copy.id);
  });

  it('post switch keeps sibling posts intact', () => {
    const a = {
      id: 'a',
      formatPreset: 'square',
      width: 1080,
      height: 1080,
      name: 'A',
      coverAssetId: SAMPLE_UUID,
      linkedProjectId: TEMPLE_UUID,
      elements: createDefaultElements(1080, 1080, { headline: 'A' }),
    };
    const b = {
      id: 'b',
      formatPreset: 'story',
      width: 1080,
      height: 1920,
      name: 'B',
      coverAssetId: null,
      linkedProjectId: TEMPLE_UUID,
      elements: createDefaultElements(1080, 1920, { headline: 'B' }),
    };
    const hydrated = hydrateSocialPostsFromDraft({
      posts: [serializeSocialPost(a), serializeSocialPost(b)],
      linkedProjectId: TEMPLE_UUID,
      selectedPostId: 'b',
    });
    assert.equal(hydrated.selectedPostId, 'b');
    assert.equal(hydrated.posts.find((p) => p.id === 'a').elements[0].content, 'A');
    assert.equal(hydrated.posts.find((p) => p.id === 'b').elements[0].content, 'B');
  });

  it('cross-project isolation keeps linked_project_id per post', () => {
    const temple = serializeSocialPost({
      id: 't',
      formatPreset: 'square',
      width: 1080,
      height: 1080,
      name: 'Temple',
      coverAssetId: SAMPLE_UUID,
      linkedProjectId: TEMPLE_UUID,
      elements: createDefaultElements(1080, 1080),
    });
    const other = serializeSocialPost({
      id: 'o',
      formatPreset: 'square',
      width: 1080,
      height: 1080,
      name: 'Other',
      coverAssetId: null,
      linkedProjectId: OTHER_UUID,
      elements: createDefaultElements(1080, 1080),
    });
    assert.notEqual(temple.linked_project_id, other.linked_project_id);
    assert.equal(parseSocialPost(other).coverAssetId, null);
  });
});

describe('AI → canvas elements', () => {
  it('writes headline/caption/CTA onto the same element model', () => {
    const elements = createDefaultElements(1080, 1080);
    const next = applyCopyToElements(elements, {
      headline: 'AI Headline',
      caption: 'AI body copy',
      cta: 'Schedule now',
    });
    assert.equal(next.find((e) => e.role === 'headline').content, 'AI Headline');
    assert.equal(next.find((e) => e.role === 'body').content, 'AI body copy');
    assert.equal(next.find((e) => e.type === 'BUTTON').label, 'Schedule now');
  });

  it('generation module exports applyGeneratedCopyToElements', () => {
    const gen = readSmb('social-media-builder-generation.ts');
    assert.match(gen, /applyGeneratedCopyToElements/);
    assert.match(gen, /applyCopyToElements/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /applyDesignResponseToPosts|generateSocialDesign/);
  });
});

describe('workspace wiring — real editor controls', () => {
  it('binds canvas to posts[].elements and selectedElementId', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /selectedElementId/);
    assert.match(workspace, /SmbArtboardElements/);
    assert.match(workspace, /selectedPost\.elements/);
    assert.match(workspace, /serializeSocialPosts/);
    assert.match(workspace, /hydrateSocialPostsFromDraft/);
    assert.doesNotMatch(workspace, /smb-ws__artboard-copy/);
  });

  it('toolbar: edit/copy/delete/layer/align are real', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /duplicateElement/);
    assert.match(workspace, /bringElementForward/);
    assert.match(workspace, /sendElementBackward/);
    assert.match(workspace, /alignElement/);
    assert.match(workspace, /smb-layer-menu/);
    assert.match(workspace, /smb-align-menu/);
  });

  it('bottom bar enables only P0 Metin/Görsel/Button', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /P0_BOTTOM_ACTIONS/);
    assert.match(workspace, /disabled: !P0_BOTTOM_ACTIONS\.has/);
    assert.match(workspace, /createTextElement/);
    assert.match(workspace, /createButtonElement/);
    assert.match(workspace, /createImageElement/);
    assert.match(workspace, /smb-element-media-picker-dialog/);
  });

  it('enables undo/redo for shared editor history; keeps send-test/publish disabled', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /data-testid="smb-send-test"[\s\S]*?disabled/);
    assert.match(workspace, /data-testid="smb-publish"[\s\S]*?disabled/);
    assert.match(workspace, /data-testid="smb-undo"/);
    assert.match(workspace, /data-testid="smb-redo"/);
    assert.match(workspace, /disabled=\{!historyPast\.length && !canUndoAiRevision\}/);
    assert.match(workspace, /disabled=\{!historyFuture\.length && !canRedoAiRevision\}/);
    assert.match(workspace, /disabled: !historyPast\.length/);
    assert.match(workspace, /undoHistory/);
    assert.match(workspace, /redoHistory/);
  });

  it('preview + PNG export use persistent post elements', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /focus\.setMode\('preview'\)/);
    assert.match(workspace, /exportSocialPostPng/);
    assert.match(workspace, /elements:\s*selectedPost\.elements/);
    assert.match(workspace, /coverImageUrl/);
    const exportSrc = readSmb('social-media-builder-export.ts');
    assert.match(exportSrc, /drawElement/);
    assert.match(exportSrc, /el\.type === 'BUTTON'/);
    assert.match(exportSrc, /export async function renderSocialPostPng/);
    assert.match(exportSrc, /export async function exportSocialPostPng/);
    assert.match(exportSrc, /await renderSocialPostPng\(input\)/);
  });

  it('Canva transfer stays available as advanced Open in Canva; PNG export unchanged', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /data-testid="smb-download-header"/);
    assert.match(workspace, /testId: 'smb-open-in-canva'/);
    assert.match(workspace, /runOpenInCanva/);
    assert.match(workspace, /runCanvaEngine/);
    assert.match(workspace, /renderSocialPostPng/);
    assert.match(workspace, /buildCanvaLayersPayload/);
    assert.match(workspace, /exportDesignToCanva/);
    assert.match(workspace, /preview_png_base64/);
    assert.match(workspace, /t\('openInCanva'\)/);
    assert.doesNotMatch(workspace, /t\('useCanvaEngine'\)/);
    assert.match(workspace, /t\('toasts.canvaReturned/);
    const platformSrc = readFileSync(join(smbDir, '../../../../../src/lib/api/platform.ts'), 'utf8');
    assert.match(platformSrc, /\/platform\/integrations\/canva\/export/);
    assert.match(platformSrc, /new FormData\(\)/);
    assert.match(platformSrc, /form.append\('layers'/);
    assert.match(platformSrc, /preview_png_base64/);
    assert.match(platformSrc, /canvaPreviewPngToObjectUrl/);
    assert.doesNotMatch(platformSrc, /Content-Type.: .application\/json.[\s\S]{0,80}canva\/export/);
    const exportSrc = readSmb('social-media-builder-export.ts');
    assert.match(exportSrc, /export function buildCanvaLayersPayload/);
    assert.match(exportSrc, /await renderSocialPostPng\(input\)/);
    const drawers = readSmb('social-media-builder-rail-drawers.tsx');
    assert.match(drawers, /data-testid="smb-settings-download"/);
    assert.match(drawers, /data-testid="smb-settings-open-in-canva"/);
    assert.match(drawers, /t\('openInCanva'\)/);
    const en = readFileSync(join(smbDir, '../../../../../messages/en.json'), 'utf8');
    const tr = readFileSync(join(smbDir, '../../../../../messages/tr.json'), 'utf8');
    assert.match(en, /"openInCanva": "Open in Canva"/);
    assert.match(tr, /"openInCanva": "Canva'da Aç"/);
    assert.match(en, /"useCanvaEngine"/);
    assert.match(tr, /"useCanvaEngine"/);
    assert.match(en, /canvaReturnedEditable/);
    assert.match(tr, /canvaReturnedEditable/);
    assert.match(en, /canvaOpenedEditable/);
    assert.match(tr, /canvaOpenedEditable/);
  });

  it('saveDraft persists posts + selectedPostId + cover Asset ID', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /posts:\s*serializeSocialPosts/);
    assert.match(workspace, /selectedPostId/);
    assert.match(workspace, /coverAssetId/);
    const persistence = readComponent('builder-media-persistence.ts');
    assert.match(persistence, /BUILDER_MEDIA_SOCIAL_POSTS_SCHEMA_VERSION/);
    assert.match(persistence, /posts\?:/);
  });

  it('no Unsplash production seeds in model defaults', () => {
    const model = readSmb('social-media-builder-model.ts');
    assert.doesNotMatch(model, /unsplash\.com/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.doesNotMatch(workspace, /unsplash\.com/);
  });

  it('IMAGE URL hydration is post-scoped and does not loop on media object identity', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    // Must not depend on coverAsset.media object identity (new every render from useCsMediaLibrary).
    assert.doesNotMatch(workspace, /\[posts,\s*coverAsset\.media\]/);
    assert.match(workspace, /useSmbPostAssetHydration/);
    assert.match(workspace, /ensureDisplayUrl:\s*coverAsset\.media\.ensureDisplayUrl/);
    assert.match(workspace, /getCachedDisplayUrl:\s*coverAsset\.media\.getCachedDisplayUrl/);
    const hydration = readSmb('social-media-builder-asset-hydration.ts');
    assert.match(hydration, /postsAssetIdsKey/);
    assert.match(hydration, /collectPostAssetIds/);
    assert.match(hydration, /canPaintResolvedAsset/);
  });
});

describe('fullscreen selection / color input safety', () => {
  it('normalizes short/alpha hex before binding color inputs', () => {
    const els = readSmb('social-media-builder-elements.ts');
    assert.match(els, /export function toColorInputValue/);
    // Mirror the shipped helper for regression coverage
    function toColorInputValue(value, fallback = '#ffffff') {
      const raw = typeof value === 'string' ? value.trim() : '';
      if (/^#[0-9a-fA-F]{6}$/.test(raw)) return raw.toLowerCase();
      if (/^#[0-9a-fA-F]{8}$/.test(raw)) return `#${raw.slice(1, 7).toLowerCase()}`;
      if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
        const r = raw[1];
        const g = raw[2];
        const b = raw[3];
        return `#${r}${r}${g}${g}${b}${b}`.toLowerCase();
      }
      return fallback;
    }
    assert.equal(toColorInputValue('#fff'), '#ffffff');
    assert.equal(toColorInputValue('#AABBCCDD'), '#aabbcc');
    assert.equal(toColorInputValue('not-a-color'), '#ffffff');
    assert.equal(toColorInputValue('#112233'), '#112233');
    const drawers = readSmb('social-media-builder-rail-drawers.tsx');
    assert.match(drawers, /toColorInputValue\(selectedElement\.backgroundColor/);
    assert.match(drawers, /toColorInputValue\(selectedElement\.textColor/);
    assert.match(drawers, /toColorInputValue\(\s*isText \? selectedElement\.color/);
  });

  it('avoids setPointerCapture/releasePointerCapture on artboard drag (FS crash)', () => {
    const binder = readSmb('smb-artboard-elements.tsx');
    assert.doesNotMatch(binder, /\.setPointerCapture\(/);
    assert.doesNotMatch(binder, /\.releasePointerCapture\(/);
    assert.match(binder, /smb-artboard-design/);
    assert.match(binder, /pointercancel/);
  });

  it('keeps AI Design inside center so fullscreen shares the same prompt state', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /\{aiDesignCommand\}/);
    assert.match(workspace, /data-testid="smb-center"[\s\S]*\{aiDesignCommand\}/);
    assert.match(workspace, /data-fs-ai=/);
  });

  it('uses safe selectElement + postsRef for FS selection and sequential AI', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /function selectElement/);
    assert.match(workspace, /onSelect=\{selectElement\}/);
    assert.match(workspace, /postsRef\.current/);
    assert.match(workspace, /selectedPostIdRef\.current/);
    assert.match(workspace, /latestPosts/);
    // Cover image clicks must not bubble into FTV capture paths
    assert.match(workspace, /smb-artboard-img[\s\S]*onPointerDown=\{\(e\) => \{\s*e\.stopPropagation\(\);\s*handleArtboardBackgroundPointerDown\(e\);\s*\}\}/);
  });

  it('guards artboard element render + drag against invalid geometry (FS)', () => {
    const binder = readSmb('smb-artboard-elements.tsx');
    assert.match(binder, /isRenderableElement/);
    assert.match(binder, /finiteOr/);
    assert.match(binder, /Do not use setPointerCapture/);
    assert.doesNotMatch(binder, /\.setPointerCapture\(/);
  });
});
