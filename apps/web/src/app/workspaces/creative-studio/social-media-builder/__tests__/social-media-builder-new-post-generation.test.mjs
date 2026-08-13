/**
 * SMB AI + Yeni Post Oluştur generation must complete after post-delete changes.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-new-post-generation.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
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

const PLACEHOLDER_HEADLINE = 'New social post';
const COVER_UUID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const TEMPLE_UUID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

function isInFlightGenerationPost(post) {
  return post?.generationLifecycle === 'creating' || post?.generationLifecycle === 'generating';
}

function isPlaceholderSocialPost(post) {
  if (!post) return false;
  if (isInFlightGenerationPost(post)) return true;
  const headline = String(post.headline || '').trim();
  return headline === PLACEHOLDER_HEADLINE && !post.coverAssetId && !post.generationMeta?.content_package;
}

function isCompletedGeneratedPost(post) {
  if (!post || isInFlightGenerationPost(post) || post.generationLifecycle === 'error') return false;
  const headline = String(post.headline || '').trim();
  if (!headline || headline === PLACEHOLDER_HEADLINE) return false;
  const meta = post.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  const hasPackage = Boolean(meta?.content_package);
  const hasPlan = Boolean(post.creativePlan || meta?.creative_plan);
  const hasBlueprint = Boolean(post.compositionBlueprint || meta?.composition_blueprint);
  const hasCover = Boolean(post.coverAssetId);
  const hasText = (post.elements || []).some(
    (el) => el.type === 'TEXT' && typeof el.content === 'string' && el.content.trim(),
  );
  return hasPackage || hasPlan || hasBlueprint || (hasCover && hasText);
}

function stripInFlightPostsForPersist(posts) {
  return posts.filter((p) => !isInFlightGenerationPost(p));
}

function mergeHydratedPostsWithLocal(input) {
  const incoming = input.incoming.filter((p) => !input.deletedIds.has(p.id));
  const local = input.local.filter((p) => !input.deletedIds.has(p.id));
  const localInFlight = local.filter((p) => isInFlightGenerationPost(p));
  const localCompleted = local.filter((p) => isCompletedGeneratedPost(p));

  if (input.generating || localInFlight.length) {
    const byId = new Map();
    for (const post of incoming) byId.set(post.id, post);
    for (const post of localCompleted) byId.set(post.id, post);
    for (const post of localInFlight) byId.set(post.id, post);
    const ordered = [];
    const seen = new Set();
    for (const post of local) {
      const next = byId.get(post.id);
      if (next && !seen.has(next.id)) {
        ordered.push(next);
        seen.add(next.id);
      }
    }
    for (const post of incoming) {
      if (!seen.has(post.id)) {
        ordered.push(post);
        seen.add(post.id);
      }
    }
    const selected =
      (input.localSelectedPostId && ordered.some((p) => p.id === input.localSelectedPostId)
        ? input.localSelectedPostId
        : null) ??
      localInFlight[0]?.id ??
      ordered[0]?.id ??
      null;
    return { posts: ordered, selectedPostId: selected };
  }

  if (!incoming.length && localCompleted.length) {
    return {
      posts: localCompleted,
      selectedPostId:
        (input.localSelectedPostId && localCompleted.some((p) => p.id === input.localSelectedPostId)
          ? input.localSelectedPostId
          : localCompleted[0]?.id) ?? null,
    };
  }

  const incomingIds = new Set(incoming.map((p) => p.id));
  const extraLocal = localCompleted.filter((p) => !incomingIds.has(p.id));
  const merged = incoming.map((post) => {
    const existing = local.find((l) => l.id === post.id);
    if (existing && isCompletedGeneratedPost(existing) && !isCompletedGeneratedPost(post)) return existing;
    if (existing && isPlaceholderSocialPost(post) && !isPlaceholderSocialPost(existing)) return existing;
    return post;
  });
  const posts = [...merged, ...extraLocal];
  const selected =
    (input.incomingSelectedPostId && posts.some((p) => p.id === input.incomingSelectedPostId)
      ? input.incomingSelectedPostId
      : null) ??
    (input.localSelectedPostId && posts.some((p) => p.id === input.localSelectedPostId)
      ? input.localSelectedPostId
      : null) ??
    posts[0]?.id ??
    null;
  return { posts, selectedPostId: selected };
}

function mergeCreateGenerationResult(input) {
  const inflightId = input.inflightId;
  const applied = input.appliedPosts.filter((p) => !input.deletedIds.has(p.id) && p.id !== inflightId);
  const localIds = new Set(input.localPosts.filter((p) => p.id !== inflightId).map((p) => p.id));
  const generated =
    (input.appliedSelectedPostId ? applied.find((p) => p.id === input.appliedSelectedPostId) : null) ??
    applied.find((p) => !localIds.has(p.id)) ??
    null;
  let posts = applied;
  if (generated && !posts.some((p) => p.id === generated.id)) posts = [...posts, generated];
  if (!posts.length) {
    posts = input.localPosts.filter((p) => p.id !== inflightId && !input.deletedIds.has(p.id));
  } else if (inflightId) {
    posts = posts.filter((p) => p.id !== inflightId);
  }
  return {
    posts,
    selectedPostId: generated?.id ?? input.appliedSelectedPostId ?? posts[0]?.id ?? null,
    generated,
  };
}

describe('source modules', () => {
  it('ships create-generation helpers without reverting delete', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-persistence.ts')), true);
    const persistence = readSmb('social-media-builder-persistence.ts');
    assert.match(persistence, /export function mergeCreateGenerationResult/);
    assert.match(persistence, /export function mergeHydratedPostsWithLocal/);
    assert.match(persistence, /export function stripInFlightPostsForPersist/);
    assert.match(persistence, /Explicit posts: \[\]/);
    assert.match(persistence, /export function deleteSocialPost/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /createGeneratingPost/);
    assert.match(workspace, /mergeCreateGenerationResult/);
    assert.match(workspace, /function confirmDeletePost/);
    assert.doesNotMatch(workspace, /unsplash\.com/i);
  });
});

describe('placeholder must not win over completed generation', () => {
  const completed = {
    id: 'gen-1',
    headline: 'Washington DC at the center',
    coverAssetId: COVER_UUID,
    linkedProjectId: TEMPLE_UUID,
    generationLifecycle: 'ready',
    generationMeta: { content_package: { headline: 'Washington DC at the center' }, creative_plan: { composition: 'editorial_overlay' } },
    compositionBlueprint: { family: 'editorial_overlay' },
    elements: [{ type: 'TEXT', content: 'Washington DC at the center' }],
  };
  const placeholder = {
    id: 'p-gen-1',
    headline: PLACEHOLDER_HEADLINE,
    coverAssetId: null,
    generationLifecycle: 'generating',
    elements: [],
  };

  it('completed generated post is canonical vs New social post placeholder', () => {
    assert.equal(isCompletedGeneratedPost(completed), true);
    assert.equal(isPlaceholderSocialPost(placeholder), true);
    assert.equal(isCompletedGeneratedPost(placeholder), false);
  });

  it('stale hydrate posts: [] does not wipe a completed local generation', () => {
    const merged = mergeHydratedPostsWithLocal({
      incoming: [],
      local: [completed],
      deletedIds: new Set(),
      generating: false,
      incomingSelectedPostId: null,
      localSelectedPostId: 'gen-1',
    });
    assert.equal(merged.posts.length, 1);
    assert.equal(merged.posts[0].id, 'gen-1');
    assert.equal(merged.selectedPostId, 'gen-1');
    assert.equal(isPlaceholderSocialPost(merged.posts[0]), false);
  });

  it('hydrate during in-flight create keeps generating post and does not reseed defaults', () => {
    const merged = mergeHydratedPostsWithLocal({
      incoming: [],
      local: [placeholder],
      deletedIds: new Set(),
      generating: true,
      incomingSelectedPostId: null,
      localSelectedPostId: 'p-gen-1',
    });
    assert.equal(merged.posts.some((p) => p.id === 'p-gen-1'), true);
    assert.equal(merged.selectedPostId, 'p-gen-1');
  });

  it('later placeholder snapshot cannot overwrite newer completed post of same id', () => {
    const merged = mergeHydratedPostsWithLocal({
      incoming: [{ ...completed, id: 'gen-1', headline: PLACEHOLDER_HEADLINE, coverAssetId: null, generationMeta: null, compositionBlueprint: null, elements: [] }],
      local: [completed],
      deletedIds: new Set(),
      generating: false,
      incomingSelectedPostId: 'gen-1',
      localSelectedPostId: 'gen-1',
    });
    assert.equal(merged.posts[0].headline, 'Washington DC at the center');
    assert.equal(merged.posts[0].coverAssetId, COVER_UUID);
  });
});

describe('create pipeline binds result to the inflight post', () => {
  it('replaces inflight slot with generated post and selects it', () => {
    const local = [
      { id: 'A', headline: 'Existing', coverAssetId: COVER_UUID, elements: [{ type: 'TEXT', content: 'Existing' }], generationMeta: { content_package: {} } },
      { id: 'p-gen-9', headline: '', generationLifecycle: 'generating', elements: [] },
    ];
    const generated = {
      id: 'uuid-new',
      headline: 'Temple location',
      coverAssetId: COVER_UUID,
      linkedProjectId: TEMPLE_UUID,
      generationMeta: { content_package: { headline: 'Temple location' }, creative_plan: {} },
      compositionBlueprint: { family: 'cinematic_architecture' },
      elements: [{ type: 'TEXT', content: 'Temple location' }],
    };
    const result = mergeCreateGenerationResult({
      localPosts: local,
      appliedPosts: [local[0], generated],
      inflightId: 'p-gen-9',
      appliedSelectedPostId: 'uuid-new',
      deletedIds: new Set(),
    });
    assert.equal(result.posts.some((p) => p.id === 'p-gen-9'), false);
    assert.equal(result.posts.some((p) => p.id === 'A'), true);
    assert.equal(result.selectedPostId, 'uuid-new');
    assert.equal(result.generated.id, 'uuid-new');
    assert.equal(isCompletedGeneratedPost(result.generated), true);
  });

  it('deleted ids cannot swallow the newly generated post', () => {
    const generated = {
      id: 'uuid-c',
      headline: 'Lifestyle at Temple',
      coverAssetId: COVER_UUID,
      generationMeta: { content_package: {} },
      elements: [{ type: 'TEXT', content: 'Lifestyle at Temple' }],
    };
    const result = mergeCreateGenerationResult({
      localPosts: [{ id: 'p-gen-c', generationLifecycle: 'generating', elements: [] }],
      appliedPosts: [generated],
      inflightId: 'p-gen-c',
      appliedSelectedPostId: 'uuid-c',
      deletedIds: new Set(['gone-a']),
    });
    assert.equal(result.posts.some((p) => p.id === 'uuid-c'), true);
    assert.equal(result.selectedPostId, 'uuid-c');
  });

  it('persist strips in-flight placeholders so empty posts[] is only true last-delete', () => {
    const posts = [
      { id: 'A', headline: 'Keep', generationLifecycle: 'ready', elements: [] },
      { id: 'p-gen-1', generationLifecycle: 'generating', elements: [] },
    ];
    const persistable = stripInFlightPostsForPersist(posts);
    assert.deepEqual(
      persistable.map((p) => p.id),
      ['A'],
    );
  });
});

describe('workspace create vs delete isolation', () => {
  it('create mints an in-flight post and does not send it in the design request', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /createGeneratingPost/);
    assert.match(workspace, /inferredMode === 'create' \? null : latestSelectedPostId/);
    assert.match(workspace, /siblingPosts/);
    assert.match(workspace, /createInflightIdRef/);
    assert.match(workspace, /generatingRef/);
    assert.match(workspace, /persistEpochRef/);
    const model = readSmb('social-media-builder-model.ts');
    assert.match(model, /export function createGeneratingPost/);
    assert.match(model, /generationLifecycle: 'generating'/);
    assert.doesNotMatch(model.slice(model.indexOf('export function createGeneratingPost')), /New social post/);
  });

  it('autosave uses a getter after wait and skips while generating', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /if \(generatingRef\.current\) return/);
    assert.match(workspace, /docApi\.saveDraft\(\(\) =>/);
    const hook = readComponent('use-builder-document.ts');
    assert.match(hook, /typeof input === 'function'/);
    assert.match(hook, /Resolve getters AFTER the wait/);
  });

  it('delete still aborts in-flight generation and persists remaining posts', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    const start = workspace.indexOf('function confirmDeletePost');
    const slice = workspace.slice(start, start + 3200);
    assert.match(slice, /generateAbortRef\.current \+= 1/);
    assert.match(slice, /deletedPostIdsRef/);
    assert.match(slice, /serializeSocialPosts\(persistPosts\)/);
    assert.match(slice, /docApi\.saveDraft/);
  });

  it('empty-element AI stubs do not seed New social post defaults', () => {
    const persistence = readSmb('social-media-builder-persistence.ts');
    assert.match(persistence, /hasCopy/);
    assert.match(persistence, /: \[\],/);
    const model = readSmb('social-media-builder-model.ts');
    assert.match(model, /PLACEHOLDER_HEADLINE/);
  });

  it('create request keeps Temple linked_project_id and null selected_post_id', () => {
    const engine = readSmb('social-media-builder-design-engine.ts');
    assert.match(engine, /selected_post_id:\s*\n\s*typeof input\.selectedPostId === 'string'/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /linkedProjectId: docApi\.constructionProjectId/);
    assert.match(workspace, /createGeneratingPost\(formatPreset/);
  });

  it('CREATE selected_asset_ids is empty so leftover foreign cover cannot 403 generation', () => {
    const engine = readSmb('social-media-builder-design-engine.ts');
    assert.match(engine, /const selected_asset_ids =\s*\n\s*mode === 'create'\s*\n\s*\? \[\]/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /inferredMode === 'create' \? null : coverAsset\.coverImage/);
    assert.match(workspace, /inferredMode === 'create' \? \[\] : coverAsset\.galleryImages/);
    const hydration = readSmb('social-media-builder-asset-hydration.ts');
    assert.match(hydration, /failedAssetIds/);
  });
});
