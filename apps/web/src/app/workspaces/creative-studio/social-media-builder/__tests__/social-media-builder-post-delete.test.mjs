/**
 * SMB Gönderiler individual post delete + gallery cleanup.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-post-delete.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const componentsDir = join(here, '../../_components');
const messagesDir = join(here, '../../../../../../messages');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

function readComponent(name) {
  return readFileSync(join(componentsDir, name), 'utf8');
}

function readMessages(name) {
  return readFileSync(join(messagesDir, name), 'utf8');
}

const SAMPLE_UUID = '11111111-1111-4111-8111-111111111111';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isMediaAssetUuid(id) {
  return Boolean(id && UUID_RE.test(String(id).trim()));
}

function collectPostAssetIds(post) {
  if (!post) return [];
  const ids = [];
  if (post.coverAssetId && isMediaAssetUuid(post.coverAssetId)) ids.push(post.coverAssetId);
  for (const el of post.elements || []) {
    if (el.type === 'IMAGE' && el.assetId && isMediaAssetUuid(el.assetId)) ids.push(el.assetId);
  }
  return [...new Set(ids)];
}

function assetUsedByOtherPosts(assetId, posts, exceptPostId) {
  if (!isMediaAssetUuid(assetId)) return false;
  for (const post of posts) {
    if (post.id === exceptPostId) continue;
    if (collectPostAssetIds(post).includes(assetId)) return true;
  }
  return false;
}

function nextSelectedPostIdAfterDelete(posts, deletedId, currentSelectedId) {
  const index = posts.findIndex((p) => p.id === deletedId);
  if (index < 0) return currentSelectedId || null;
  if (currentSelectedId && currentSelectedId !== deletedId) return currentSelectedId;
  const remaining = posts.filter((p) => p.id !== deletedId);
  if (!remaining.length) return null;
  return remaining[index]?.id ?? remaining[index - 1]?.id ?? remaining[0]?.id ?? null;
}

function deleteSocialPost(posts, postId, selectedPostId) {
  const deleted = posts.find((p) => p.id === postId) ?? null;
  if (!deleted) return { posts, selectedPostId: selectedPostId ?? null, deleted: null };
  return {
    posts: posts.filter((p) => p.id !== postId),
    selectedPostId: nextSelectedPostIdAfterDelete(posts, postId, selectedPostId),
    deleted,
  };
}

function hydrateSocialPostsFromDraft(input) {
  const parsed = Array.isArray(input.posts) ? input.posts.filter(Boolean) : [];
  if (parsed.length) {
    const selected =
      input.selectedPostId && parsed.some((p) => p.id === input.selectedPostId)
        ? input.selectedPostId
        : parsed[0].id;
    return { posts: parsed, selectedPostId: selected };
  }
  if (Array.isArray(input.posts)) {
    return { posts: [], selectedPostId: null };
  }
  return { posts: [{ id: 'default' }], selectedPostId: 'default' };
}

describe('source modules', () => {
  it('ships delete helpers and overflow menu', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-persistence.ts')), true);
    assert.equal(existsSync(join(smbDir, 'smb-post-overflow-menu.tsx')), true);
    const persistence = readSmb('social-media-builder-persistence.ts');
    assert.match(persistence, /export function nextSelectedPostIdAfterDelete/);
    assert.match(persistence, /export function deleteSocialPost/);
    assert.match(persistence, /Explicit posts: \[\]/);
  });
});

describe('selection fallback', () => {
  const posts = [{ id: 'A' }, { id: 'B' }, { id: 'C' }, { id: 'D' }];

  it('delete B while B selected → C', () => {
    const result = deleteSocialPost(posts, 'B', 'B');
    assert.deepEqual(
      result.posts.map((p) => p.id),
      ['A', 'C', 'D'],
    );
    assert.equal(result.selectedPostId, 'C');
  });

  it('delete D while D selected → C', () => {
    const result = deleteSocialPost(posts, 'D', 'D');
    assert.equal(result.selectedPostId, 'C');
    assert.equal(result.posts.some((p) => p.id === 'D'), false);
  });

  it('delete unselected B while A selected → keep A', () => {
    const result = deleteSocialPost(posts, 'B', 'A');
    assert.equal(result.selectedPostId, 'A');
    assert.equal(result.posts.some((p) => p.id === 'B'), false);
  });

  it('delete last remaining post → empty', () => {
    const result = deleteSocialPost([{ id: 'Z' }], 'Z', 'Z');
    assert.equal(result.posts.length, 0);
    assert.equal(result.selectedPostId, null);
  });
});

describe('persistence of deleted posts', () => {
  it('hydrate keeps explicit empty posts[] (no DEFAULT reseed)', () => {
    const empty = hydrateSocialPostsFromDraft({ posts: [], selectedPostId: 'gone' });
    assert.equal(empty.posts.length, 0);
    assert.equal(empty.selectedPostId, null);
  });

  it('hydrate still seeds when posts field is missing', () => {
    const seeded = hydrateSocialPostsFromDraft({ selectedPostId: null });
    assert.ok(seeded.posts.length > 0);
  });

  it('deleted post is absent after hydrate of remaining posts', () => {
    const hydrated = hydrateSocialPostsFromDraft({
      posts: [{ id: 'A' }, { id: 'C' }],
      selectedPostId: 'C',
    });
    assert.equal(hydrated.posts.some((p) => p.id === 'B'), false);
    assert.equal(hydrated.selectedPostId, 'C');
  });

  it('serializeBuilderMediaDraft persists empty posts[]', () => {
    const src = readComponent('builder-media-persistence.ts');
    assert.match(src, /const postsProvided = Array\.isArray\(input\.posts\)/);
    assert.match(src, /draft\.posts = input\.posts/);
    assert.match(src, /draft\.selectedPostId = input\.selectedPostId \?\? null/);
    assert.match(src, /hasPostsField/);
  });

  it('workspace persists delete via saveDraft with serialized posts', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /function confirmDeletePost/);
    assert.match(workspace, /deleteSocialPost/);
    assert.match(workspace, /serializeSocialPosts\(persistPosts\)/);
    assert.match(workspace, /docApi\.saveDraft/);
    assert.match(workspace, /selectedPostId: result\.selectedPostId/);
  });
});

describe('asset safety', () => {
  it('shared asset X remains used after deleting B', () => {
    const posts = [
      { id: 'A', coverAssetId: SAMPLE_UUID, elements: [] },
      { id: 'B', coverAssetId: SAMPLE_UUID, elements: [] },
    ];
    const remaining = deleteSocialPost(posts, 'B', 'B').posts;
    assert.equal(assetUsedByOtherPosts(SAMPLE_UUID, remaining, 'B'), true);
    assert.equal(remaining.find((p) => p.id === 'A').coverAssetId, SAMPLE_UUID);
  });

  it('delete path does not revoke/invalidate shared assets', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    const start = workspace.indexOf('function confirmDeletePost');
    assert.ok(start >= 0);
    const slice = workspace.slice(start, start + 2800);
    assert.doesNotMatch(slice, /revokeObjectURL/);
    assert.doesNotMatch(slice, /invalidateAsset/);
    assert.match(slice, /do not revoke URLs still used/i);
  });
});

describe('workspace wiring', () => {
  it('contextual ••• menu + DS confirm, not always-visible delete buttons', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /SmbPostCardMore/);
    const menu = readSmb('smb-post-overflow-menu.tsx');
    assert.match(menu, /smb-post-more-/);
    assert.match(workspace, /deleteConfirm\.title/);
    assert.match(workspace, /variant="danger"/);
    assert.match(workspace, /data-testid="smb-post-delete-confirm"/);
    assert.match(workspace, /from '@investhome\/ui'/);
    assert.match(workspace, /Dialog/);
    assert.doesNotMatch(workspace, /smb-filmstrip-delete/);
    const css = readSmb('social-media-builder.css');
    assert.match(css, /\.smb-ws__page-more/);
    assert.match(css, /\.smb-ws__page-card:hover \.smb-ws__page-more/);
  });

  it('••• click does not select another post (stopPropagation)', () => {
    const menu = readSmb('smb-post-overflow-menu.tsx');
    assert.match(menu, /e\.stopPropagation\(\)/);
    assert.match(menu, /smb-ws__page-more/);
  });

  it('does not add keyboard Delete/Backspace for posts', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    const start = workspace.indexOf("event.key === 'Delete' || event.key === 'Backspace'");
    assert.ok(start >= 0);
    const slice = workspace.slice(start, start + 700);
    assert.match(slice, /elementRemoved/);
    assert.doesNotMatch(slice, /confirmDeletePost/);
    assert.doesNotMatch(slice, /deleteSocialPost/);
  });

  it('invalidates in-flight generation and waits for saveDraft', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /generateAbortRef\.current \+= 1/);
    assert.match(workspace, /deletedPostIdsRef/);
    const hook = readComponent('use-builder-document.ts');
    assert.match(hook, /Wait out in-flight saves/);
    assert.match(hook, /savingRef\.current/);
  });

  it('clears canvas state when last post is deleted', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /coverAsset\.clearCover\(\)/);
    assert.match(workspace, /setGenerationMeta\(null\)/);
    assert.match(workspace, /selectedPost\?\.elements \?\? \[\]/);
    assert.match(workspace, /smb-new-post/);
  });

  it('i18n uses required Turkish confirm copy', () => {
    const tr = readMessages('tr.json');
    assert.match(tr, /"title": "Gönderiyi sil"/);
    assert.match(tr, /"message": "Bu gönderiyi silmek istediğinize emin misiniz\?"/);
    assert.match(tr, /"cancel": "Vazgeç"/);
    assert.match(tr, /"confirm": "Sil"/);
    assert.match(tr, /"postDeleted": "Gönderi silindi"/);
  });
});
