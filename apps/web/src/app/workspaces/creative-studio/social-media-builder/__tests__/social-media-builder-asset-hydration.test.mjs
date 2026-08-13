/**
 * SMB per-post Drive asset rehydration (switch / reload / fullscreen).
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-asset-hydration.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const componentsDir = join(here, '../../_components');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

function readComponent(name) {
  return readFileSync(join(componentsDir, name), 'utf8');
}

const UUID_A = '11111111-1111-4111-8111-111111111111';
const UUID_B = '22222222-2222-4222-8222-222222222222';
const UUID_C = '33333333-3333-4333-8333-333333333333';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isMediaAssetUuid(id) {
  return Boolean(id && UUID_RE.test(String(id).trim()));
}

function uniqueAssetIds(ids) {
  const seen = new Set();
  const out = [];
  for (const id of ids) {
    if (!isMediaAssetUuid(id) || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

function collectElementAssetIds(elements) {
  if (!elements?.length) return [];
  const ids = [];
  for (const el of elements) {
    if (el.type === 'IMAGE' && el.assetId && isMediaAssetUuid(el.assetId)) ids.push(el.assetId);
  }
  return uniqueAssetIds(ids);
}

function collectPostAssetIds(post) {
  if (!post) return [];
  const ids = [];
  if (post.coverAssetId && isMediaAssetUuid(post.coverAssetId)) ids.push(post.coverAssetId);
  ids.push(...collectElementAssetIds(post.elements));
  return uniqueAssetIds(ids);
}

function collectAllPostsAssetIds(posts, selectedPostId) {
  const selected = posts.find((p) => p.id === selectedPostId);
  const ordered = [];
  if (selected) ordered.push(...collectPostAssetIds(selected));
  for (const post of posts) {
    if (post.id === selectedPostId) continue;
    ordered.push(...collectPostAssetIds(post));
  }
  return uniqueAssetIds(ordered);
}

function deriveArtboardState(coverAssetId, displayById) {
  const id = coverAssetId && isMediaAssetUuid(coverAssetId) ? coverAssetId : null;
  if (!id) return { src: null, state: 'empty' };
  const entry = displayById[id];
  if (entry?.status === 'ready' && entry.url) return { src: entry.url, state: 'ready' };
  if (entry?.status === 'error') return { src: null, state: 'error' };
  return { src: null, state: 'loading' };
}

function canPaintResolvedAsset(input) {
  if (input.requestPostId !== input.selectedPostId) return false;
  if (!input.selectedCoverAssetId) return false;
  return input.requestAssetId === input.selectedCoverAssetId;
}

function assetUsedByOtherPosts(assetId, posts, exceptPostId) {
  if (!isMediaAssetUuid(assetId)) return false;
  for (const post of posts) {
    if (post.id === exceptPostId) continue;
    if (collectPostAssetIds(post).includes(assetId)) return true;
  }
  return false;
}

function serializeCover(assetId, url) {
  const id = assetId && isMediaAssetUuid(assetId) ? assetId : null;
  const ephemeral =
    typeof url === 'string' &&
    (url.startsWith('blob:') || url.startsWith('object:') || url.startsWith('filesystem:'));
  return id ? { asset_id: id, url: null } : ephemeral ? null : null;
}

const postA = {
  id: 'post-a',
  coverAssetId: UUID_A,
  linkedProjectId: 'd50708cb-60b3-465a-8b16-6d30f802af8d',
  elements: [{ type: 'IMAGE', assetId: UUID_C }],
};
const postB = {
  id: 'post-b',
  coverAssetId: UUID_B,
  linkedProjectId: 'd50708cb-60b3-465a-8b16-6d30f802af8d',
  elements: [],
};

describe('canonical Asset ID helpers', () => {
  it('collects cover + IMAGE element IDs and ignores blob URLs', () => {
    const ids = collectPostAssetIds({
      id: 'p1',
      coverAssetId: 'blob:http://localhost/abc',
      elements: [
        { type: 'IMAGE', assetId: UUID_A },
        { type: 'TEXT', assetId: UUID_B },
        { type: 'IMAGE', assetId: 'not-a-uuid' },
      ],
    });
    assert.deepEqual(ids, [UUID_A]);
  });

  it('orders selected post assets first for fetch priority', () => {
    const ids = collectAllPostsAssetIds([postA, postB], 'post-b');
    assert.equal(ids[0], UUID_B);
    assert.ok(ids.includes(UUID_A));
    assert.ok(ids.includes(UUID_C));
  });

  it('persists Asset ID only — never blob URLs', () => {
    assert.deepEqual(serializeCover(UUID_A, 'blob:http://localhost/x'), {
      asset_id: UUID_A,
      url: null,
    });
    assert.equal(serializeCover('blob:http://localhost/x', 'blob:http://localhost/x'), null);
  });
});

describe('artboard state + race isolation', () => {
  it('LOADING / READY / ERROR / EMPTY from selected cover Asset ID', () => {
    assert.equal(deriveArtboardState(null, {}).state, 'empty');
    assert.equal(deriveArtboardState(UUID_A, {}).state, 'loading');
    assert.deepEqual(deriveArtboardState(UUID_A, { [UUID_A]: { status: 'ready', url: 'blob:a' } }), {
      src: 'blob:a',
      state: 'ready',
    });
    assert.equal(deriveArtboardState(UUID_A, { [UUID_A]: { status: 'error', url: null } }).state, 'error');
  });

  it('post A response must not paint on selected post B', () => {
    assert.equal(
      canPaintResolvedAsset({
        requestPostId: 'post-a',
        requestAssetId: UUID_A,
        selectedPostId: 'post-b',
        selectedCoverAssetId: UUID_B,
      }),
      false,
    );
    assert.equal(
      canPaintResolvedAsset({
        requestPostId: 'post-b',
        requestAssetId: UUID_B,
        selectedPostId: 'post-b',
        selectedCoverAssetId: UUID_B,
      }),
      true,
    );
  });

  it('A→B→A uses per-asset cache so B cannot invalidate A', () => {
    const cache = {
      [UUID_A]: { status: 'ready', url: 'blob:a' },
      [UUID_B]: { status: 'ready', url: 'blob:b' },
    };
    assert.equal(deriveArtboardState(UUID_A, cache).src, 'blob:a');
    assert.equal(deriveArtboardState(UUID_B, cache).src, 'blob:b');
    assert.equal(deriveArtboardState(UUID_A, cache).src, 'blob:a');
    assert.equal(assetUsedByOtherPosts(UUID_A, [postA, postB], 'post-b'), true);
    assert.equal(assetUsedByOtherPosts(UUID_B, [postA, postB], 'post-b'), false);
  });
});

describe('workspace wiring', () => {
  it('rehydrates on selectedPostId from persisted coverAssetId — not blob URLs', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /useSmbPostAssetHydration/);
    assert.match(workspace, /selectedPostId/);
    assert.match(workspace, /coverAssetId/);
    assert.match(workspace, /linkedProjectId:\s*docApi\.constructionProjectId/);
    assert.match(workspace, /Canonical persist: Asset ID only/);
    assert.match(workspace, /thumbUrl: ''/);
    assert.match(workspace, /Do not hydrateMedia here/);
    const selectStart = workspace.indexOf('function selectPost');
    assert.ok(selectStart >= 0, 'expected selectPost');
    const selectSlice = workspace.slice(selectStart, selectStart + 900);
    assert.doesNotMatch(selectSlice, /coverAsset\.hydrateMedia/);
  });

  it('CREATE/EDIT share the same hydration path as reload', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /applyDesignResponseToPosts/);
    assert.match(workspace, /setSelectedPostId\(applied\.selectedPostId\)/);
    assert.match(workspace, /setCoverImage/);
    assert.match(workspace, /invalidateAsset/);
    assert.match(workspace, /assetUsedByOtherPosts/);
  });

  it('fullscreen uses the same artboardSrc — no second image state', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /data-testid="smb-artboard-img"/);
    assert.match(workspace, /src=\{artboardSrc\}/);
    assert.match(workspace, /postAssets\.retryAsset/);
    assert.doesNotMatch(workspace, /fsCoverUrl|fullscreenSrc|fsDisplayUrl/);
    assert.match(workspace, /data-cs-fullscreen=\{focus\.isFullscreen \? 'true' : 'false'\}/);
  });

  it('loading times out to recoverable error and preserves linked project scope', () => {
    const hydration = readSmb('social-media-builder-asset-hydration.ts');
    assert.match(hydration, /SMB_ASSET_RESOLVE_TIMEOUT_MS/);
    assert.match(hydration, /status: 'error'/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /scopeToLinkedProject:\s*true/);
    assert.match(workspace, /linkedProjectId: docApi\.constructionProjectId/);
    const media = readComponent('use-cs-media-library.ts');
    assert.match(media, /linked_project_id:\s*scopeId/);
    assert.match(media, /switched = scopedProjectRef/);
    assert.match(media, /Do NOT revoke object URLs when only fetchList identity changes/);
  });
});
