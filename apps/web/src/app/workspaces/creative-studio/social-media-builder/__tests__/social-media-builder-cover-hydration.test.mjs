/**
 * Stale SMB draft must not keep v2 when campaign master current cover is v3.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-cover-hydration.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const persistence = readFileSync(join(here, '..', 'social-media-builder-persistence.ts'), 'utf8');
const workspace = readFileSync(join(here, '..', 'social-media-builder-workspace.tsx'), 'utf8');

const V2 = '19ed9f2c-3378-4eb4-9387-ed78b9f3768f';
const V3 = '7e3825a3-69a8-4339-b619-3df01be56f20';
const FAILED = '647e8e78-be87-482e-9236-fa1edf539e85';
const CAMPAIGN = 'e67f94ea-a52f-4bde-9fd6-1c126cc5a2b5';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isMediaAssetUuid(value) {
  return typeof value === 'string' && UUID_RE.test(value.trim());
}

function resolveCampaignMasterCover(source) {
  if (!source) return null;
  const ctx =
    source.campaign_context && typeof source.campaign_context === 'object'
      ? source.campaign_context
      : null;
  const mcRaw = ctx?.master_creative ?? source.master_creative;
  const mc = mcRaw && typeof mcRaw === 'object' ? mcRaw : {};
  const coverRaw =
    mc.current_cover_asset_id ??
    (ctx ? ctx.current_cover_asset_id : null) ??
    source.current_cover_asset_id;
  const cover = typeof coverRaw === 'string' && isMediaAssetUuid(coverRaw) ? coverRaw.trim() : null;
  if (!cover) return null;
  const versionRaw = mc.current_version ?? (ctx ? ctx.current_version : null);
  const version = typeof versionRaw === 'number' ? versionRaw : Number(versionRaw);
  return {
    coverAssetId: cover,
    currentVersion: Number.isFinite(version) ? version : null,
  };
}

function readPersistedCoverVersion(post) {
  const meta = post?.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  const raw = meta?.current_version ?? meta?.cover_version;
  const n = typeof raw === 'number' ? raw : Number(raw);
  return Number.isFinite(n) ? n : null;
}

function applyNewerMasterCoverToPost(post, master) {
  const cover = master.coverAssetId;
  const localVersion = readPersistedCoverVersion(post);
  if (master.currentVersion != null && localVersion != null && master.currentVersion < localVersion) {
    return post;
  }
  if (post.coverAssetId === cover && localVersion === master.currentVersion) {
    const gpt = post.generationMeta?.gpt_image || {};
    const bg = post.elements.find((el) => el.type === 'IMAGE' && el.id === 'img-finished-ad');
    if (
      post.generationMeta?.finished_ad_raster_asset_id === cover &&
      gpt.local_asset_id === cover &&
      (!bg || bg.assetId === cover)
    ) {
      return post;
    }
  }
  const previous = post.coverAssetId;
  return {
    ...post,
    coverAssetId: cover,
    thumbUrl: '',
    elements: post.elements.map((el) =>
      el.type === 'IMAGE' &&
      (el.id === 'img-finished-ad' || el.role === 'background' || el.assetId === previous)
        ? { ...el, assetId: cover }
        : el,
    ),
    generationMeta: {
      ...post.generationMeta,
      current_version: master.currentVersion,
      finished_ad_raster_asset_id: cover,
      gpt_image: { ...(post.generationMeta?.gpt_image || {}), local_asset_id: cover },
    },
  };
}

function pickNewerCoverPost(existing, incoming) {
  const existingVersion = readPersistedCoverVersion(existing);
  const incomingVersion = readPersistedCoverVersion(incoming);
  if (existing.coverAssetId && incoming.coverAssetId && existing.coverAssetId !== incoming.coverAssetId) {
    if (existingVersion != null && incomingVersion != null) {
      if (existingVersion > incomingVersion) return existing;
      if (incomingVersion > existingVersion) return incoming;
    }
    if (existingVersion != null && incomingVersion == null) return existing;
    if (incomingVersion != null && existingVersion == null) return incoming;
  }
  return incoming;
}

function staleDraftPost() {
  return {
    id: 'ad357b88-36ab-469a-a4ac-45700fade56d',
    campaignContextId: CAMPAIGN,
    coverAssetId: V2,
    elements: [{ id: 'img-finished-ad', type: 'IMAGE', role: 'background', assetId: V2 }],
    generationMeta: {
      production_mode: 'finished_ad',
      generated_by: 'creative_director_generate_ad',
      finished_ad_raster_asset_id: FAILED,
      gpt_image: { local_asset_id: V2, editable_layers: false },
    },
  };
}

describe('v3 cover hydration — source wiring', () => {
  it('persistence exports master-cover helpers', () => {
    assert.match(persistence, /export function resolveCampaignMasterCover/);
    assert.match(persistence, /export function applyNewerMasterCoverToPost/);
    assert.match(persistence, /export function applyNewerMasterCoverToPosts/);
    assert.match(persistence, /export function shouldPreferMasterCover/);
    assert.match(persistence, /pickNewerCoverPost\(existing, post\)/);
    assert.match(persistence, /current_version/);
  });

  it('SMB hydrate applies campaign current cover after GET', () => {
    assert.match(workspace, /resolveCampaignMasterCover\(camp\)/);
    assert.match(workspace, /applyNewerMasterCoverToPosts/);
    assert.match(workspace, /getCreativeDirectorCampaign\(campaignId\)/);
    assert.match(workspace, /resolveCampaignMasterCover\(response\)/);
    assert.match(workspace, /applyNewerMasterCoverToPost\(nextPost, masterCover\)/);
  });
});

describe('v3 cover hydration — behavior', () => {
  it('reads v3 current cover from campaign_context', () => {
    const master = resolveCampaignMasterCover({
      campaign_context: {
        current_cover_asset_id: V3,
        master_creative: { current_cover_asset_id: V3, current_version: 3 },
      },
    });
    assert.equal(master.coverAssetId, V3);
    assert.equal(master.currentVersion, 3);
  });

  it('replaces stale v2 draft pointers with persisted v3', () => {
    const next = applyNewerMasterCoverToPost(staleDraftPost(), {
      coverAssetId: V3,
      currentVersion: 3,
    });
    assert.equal(next.coverAssetId, V3);
    assert.equal(next.elements[0].assetId, V3);
    assert.equal(next.generationMeta.finished_ad_raster_asset_id, V3);
    assert.equal(next.generationMeta.gpt_image.local_asset_id, V3);
    assert.equal(next.generationMeta.current_version, 3);
  });

  it('does not let unversioned v2 draft overwrite local v3', () => {
    const localV3 = applyNewerMasterCoverToPost(staleDraftPost(), {
      coverAssetId: V3,
      currentVersion: 3,
    });
    const picked = pickNewerCoverPost(localV3, staleDraftPost());
    assert.equal(picked.coverAssetId, V3);
  });
});
