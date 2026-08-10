/**
 * Social Media Builder ↔ shared Creative Studio generation wiring.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-generation.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const apiClientPath = join(here, '../../../../../lib/api/creative-studio.ts');

function readSmb(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

const SAMPLE_UUID = '11111111-1111-4111-8111-111111111111';
const TEMPLE_UUID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const OTHER_UUID = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';
const COVER_UUID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const GALLERY_UUID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isMediaAssetUuid(id) {
  return Boolean(id && UUID_RE.test(String(id).trim()));
}

function collectSelectedAssetIds(coverImage, galleryImages) {
  const ids = [];
  const seen = new Set();
  const push = (raw) => {
    if (!raw || !isMediaAssetUuid(raw)) return;
    const id = String(raw).trim();
    if (seen.has(id)) return;
    seen.add(id);
    ids.push(id);
  };
  push(coverImage?.asset_id);
  for (const ref of galleryImages ?? []) push(ref?.asset_id);
  return ids;
}

function assertNoRawMediaUrls(assetIds) {
  return assetIds.every((id) => {
    if (!id || typeof id !== 'string') return false;
    const trimmed = id.trim();
    if (/^https?:\/\//i.test(trimmed) || /drive\.google/i.test(trimmed)) return false;
    return UUID_RE.test(trimmed);
  });
}

function buildSocialGenerateRequest(input) {
  const linked = typeof input.linkedProjectId === 'string' ? input.linkedProjectId.trim() : '';
  if (!linked || !UUID_RE.test(linked)) {
    return { ok: false, reason: 'missing_project' };
  }
  const instruction = (input.instruction || '').trim();
  if (!instruction) {
    return { ok: false, reason: 'missing_instruction' };
  }
  const selected_asset_ids = collectSelectedAssetIds(input.coverImage, input.galleryImages).filter(
    (id) => UUID_RE.test(id) && !/^https?:/i.test(id),
  );
  const platforms = input.platforms ? Array.from(input.platforms).map(String).filter(Boolean) : [];
  const builder_context = { builder: 'social' };
  if (platforms.length) builder_context.platforms = platforms;
  if (input.formatPreset) builder_context.format_preset = input.formatPreset;
  if (input.format) builder_context.format = input.format;
  if (input.platform) builder_context.platform = input.platform;
  if (input.postName) builder_context.post_name = input.postName;

  return {
    ok: true,
    request: {
      linked_project_id: linked,
      builder_type: 'social',
      instruction,
      selected_asset_ids,
      language: input.language?.trim() || null,
      builder_context,
    },
  };
}

function applyGeneratedCopyToPost(content) {
  const text = (content || '').trim();
  if (!text) return {};
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  const first = lines[0] ?? text;
  const rest = lines.slice(1).join('\n').trim();
  const headline = first.length <= 120 ? first : `${first.slice(0, 117).trimEnd()}…`;
  return { headline, caption: rest || text, description: text };
}

function hasInsufficientContext(response) {
  if (response.grounded === false) return true;
  return (response.warnings ?? []).some(
    (w) =>
      w === 'insufficient_context' ||
      w === 'insufficient_retrieved_content' ||
      String(w).includes('insufficient'),
  );
}

describe('source modules exist', () => {
  it('ships generation helper + workspace', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-generation.ts')), true);
    assert.equal(existsSync(join(smbDir, 'social-media-builder-workspace.tsx')), true);
    assert.equal(existsSync(apiClientPath), true);
  });
});

describe('API client generateCreativeStudioContent', () => {
  it('posts to /ai/creative-studio/generate with typed request fields', () => {
    const client = readFileSync(apiClientPath, 'utf8');
    assert.match(client, /export async function generateCreativeStudioContent/);
    assert.match(client, /\/ai\/creative-studio\/generate/);
    assert.match(client, /linked_project_id/);
    assert.match(client, /builder_type/);
    assert.match(client, /selected_asset_ids/);
    assert.match(client, /builder_context/);
    assert.match(client, /CreativeStudioGenerateRequest/);
    assert.match(client, /CreativeStudioGenerateResponse/);
  });
});

describe('request payload for Temple social generation', () => {
  it('builds social request with linked_project_id, asset ids, language, platform context', () => {
    const built = buildSocialGenerateRequest({
      linkedProjectId: TEMPLE_UUID,
      instruction: 'Write an Instagram caption for soft launch',
      coverImage: { asset_id: COVER_UUID, url: null },
      galleryImages: [{ asset_id: GALLERY_UUID }],
      language: 'en',
      platforms: new Set(['instagram', 'linkedin']),
      formatPreset: 'square',
      platform: 'instagram',
      postName: 'Soft launch',
      format: 'feed',
    });
    assert.equal(built.ok, true);
    assert.equal(built.request.linked_project_id, TEMPLE_UUID);
    assert.equal(built.request.builder_type, 'social');
    assert.equal(built.request.instruction, 'Write an Instagram caption for soft launch');
    assert.deepEqual(built.request.selected_asset_ids, [COVER_UUID, GALLERY_UUID]);
    assert.equal(built.request.language, 'en');
    assert.equal(built.request.builder_context.builder, 'social');
    assert.deepEqual(built.request.builder_context.platforms, ['instagram', 'linkedin']);
    assert.equal(built.request.builder_context.platform, 'instagram');
    assert.equal(built.request.builder_context.format_preset, 'square');
  });

  it('never puts Drive / http URLs into selected_asset_ids', () => {
    const built = buildSocialGenerateRequest({
      linkedProjectId: TEMPLE_UUID,
      instruction: 'Caption please',
      coverImage: {
        asset_id: COVER_UUID,
        url: 'https://drive.google.com/file/d/abc/view',
      },
      galleryImages: [
        { asset_id: 'https://drive.google.com/uc?id=x' },
        { asset_id: 'not-a-uuid' },
        { asset_id: GALLERY_UUID },
      ],
    });
    assert.equal(built.ok, true);
    assert.deepEqual(built.request.selected_asset_ids, [COVER_UUID, GALLERY_UUID]);
    assert.equal(assertNoRawMediaUrls(built.request.selected_asset_ids), true);
    for (const id of built.request.selected_asset_ids) {
      assert.doesNotMatch(id, /^https?:/i);
      assert.doesNotMatch(id, /drive\.google/i);
    }
  });

  it('rejects missing linked project (UI path reason)', () => {
    const missing = buildSocialGenerateRequest({
      linkedProjectId: null,
      instruction: 'Write caption',
    });
    assert.equal(missing.ok, false);
    assert.equal(missing.reason, 'missing_project');

    const blank = buildSocialGenerateRequest({
      linkedProjectId: '   ',
      instruction: 'Write caption',
    });
    assert.equal(blank.ok, false);
    assert.equal(blank.reason, 'missing_project');
  });

  it('rejects empty instruction', () => {
    const built = buildSocialGenerateRequest({
      linkedProjectId: TEMPLE_UUID,
      instruction: '  ',
    });
    assert.equal(built.ok, false);
    assert.equal(built.reason, 'missing_instruction');
  });
});

describe('project isolation', () => {
  it('keeps Temple and other project ids distinct in payload', () => {
    const temple = buildSocialGenerateRequest({
      linkedProjectId: TEMPLE_UUID,
      instruction: 'Temple caption',
      coverImage: { asset_id: COVER_UUID },
    });
    const other = buildSocialGenerateRequest({
      linkedProjectId: OTHER_UUID,
      instruction: 'Other caption',
      coverImage: { asset_id: SAMPLE_UUID },
    });
    assert.equal(temple.ok, true);
    assert.equal(other.ok, true);
    assert.notEqual(temple.request.linked_project_id, other.request.linked_project_id);
    assert.notDeepEqual(temple.request.selected_asset_ids, other.request.selected_asset_ids);
  });

  it('generation helper + workspace clear meta on project change', () => {
    const gen = readSmb('social-media-builder-generation.ts');
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(gen, /builder_type:\s*'social'/);
    assert.match(gen, /collectSelectedAssetIds/);
    assert.match(gen, /assertNoRawMediaUrls/);
    assert.match(workspace, /setGenerationMeta\(null\)/);
    assert.match(workspace, /handleProjectChange/);
  });
});

describe('copy apply + insufficient context', () => {
  it('maps generated content into existing editor fields', () => {
    const patch = applyGeneratedCopyToPost('Quiet Luxury\nDiscover Temple Residences today.');
    assert.equal(patch.headline, 'Quiet Luxury');
    assert.equal(patch.caption, 'Discover Temple Residences today.');
    assert.equal(patch.description, 'Quiet Luxury\nDiscover Temple Residences today.');
  });

  it('flags insufficient_context / ungrounded responses', () => {
    assert.equal(
      hasInsufficientContext({ grounded: false, warnings: [] }),
      true,
    );
    assert.equal(
      hasInsufficientContext({
        grounded: true,
        warnings: ['insufficient_context'],
      }),
      true,
    );
    assert.equal(
      hasInsufficientContext({ grounded: true, warnings: [] }),
      false,
    );
  });
});

describe('workspace wires shared generate API (no toast/fake AI)', () => {
  it('calls generateCreativeStudioContent and drops runAiDemo', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /generateCreativeStudioContent/);
    assert.match(workspace, /buildSocialGenerateRequest/);
    assert.match(workspace, /runAiGenerate/);
    assert.match(workspace, /toasts\.projectRequired/);
    assert.match(workspace, /toasts\.insufficientContext/);
    assert.match(workspace, /setGenerationMeta/);
    assert.match(workspace, /applyGeneratedCopyToPost/);
    assert.match(workspace, /constructionProjectId/);
    assert.match(workspace, /coverAsset\.coverImage/);
    assert.doesNotMatch(workspace, /runAiDemo/);
    assert.doesNotMatch(workspace, /AI_STATUS_SEQUENCE/);
  });

  it('AiDrawer uses onGenerate instead of toast-only demo', () => {
    const drawers = readSmb('social-media-builder-rail-drawers.tsx');
    assert.match(drawers, /onGenerate\?:/);
    assert.match(drawers, /onGenerate\(instruction\)/);
    assert.match(drawers, /toasts\.instructionRequired/);
    assert.doesNotMatch(drawers, /onToast\(t\('rails\.ai\.generated'\)\)/);
  });

  it('generation helper module exports request builders', () => {
    const gen = readSmb('social-media-builder-generation.ts');
    assert.match(gen, /export function buildSocialGenerateRequest/);
    assert.match(gen, /export function collectSelectedAssetIds/);
    assert.match(gen, /export function applyGeneratedCopyToPost/);
    assert.match(gen, /export function hasInsufficientContext/);
    assert.match(gen, /export function toGenerationMeta/);
    assert.match(gen, /builder_type:\s*'social'/);
  });
});
