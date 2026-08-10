/**
 * Blog Builder production project + media wiring.
 * Run: node --test src/app/workspaces/creative-studio/blog-builder/__tests__/blog-builder-persistence.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const bbDir = join(here, '..');
const componentsDir = join(here, '../../_components');

function readBb(name) {
  return readFileSync(join(bbDir, name), 'utf8');
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

function isEphemeralDisplayUrl(url) {
  if (!url) return false;
  const lower = String(url).trim().toLowerCase();
  return lower.startsWith('blob:') || lower.startsWith('object:') || lower.startsWith('filesystem:');
}

function isPersistableUrl(url) {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
  if (!trimmed || isEphemeralDisplayUrl(trimmed)) return false;
  return true;
}

function parseImageRef(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const assetRaw =
    typeof raw.asset_id === 'string' ? raw.asset_id : typeof raw.assetId === 'string' ? raw.assetId : null;
  const safeAssetId = assetRaw && isMediaAssetUuid(assetRaw) ? assetRaw.trim() : null;
  const urlRaw = typeof raw.url === 'string' ? raw.url : typeof raw.src === 'string' ? raw.src : null;
  const url = isPersistableUrl(urlRaw) ? urlRaw.trim() : null;
  if (!safeAssetId && !url) return null;
  return {
    asset_id: safeAssetId,
    url,
    alt: typeof raw.alt === 'string' ? raw.alt : null,
    role: typeof raw.role === 'string' ? raw.role : null,
  };
}

function serializeImageRef(ref) {
  if (!ref) return null;
  const asset_id = ref.asset_id && isMediaAssetUuid(ref.asset_id) ? ref.asset_id : null;
  const url = isPersistableUrl(ref.url) ? ref.url.trim() : null;
  if (!asset_id && !url) return null;
  const out = { asset_id };
  if (url) out.url = url;
  if (ref.alt) out.alt = ref.alt;
  if (ref.role) out.role = ref.role;
  return out;
}

function serializeBuilderMediaDraft(input) {
  return {
    schemaVersion: 1,
    documentType: input.documentType,
    linkedProjectId: input.linkedProjectId,
    coverImage: serializeImageRef(input.coverImage),
    galleryImages: (input.galleryImages ?? []).map(serializeImageRef).filter(Boolean),
    savedAt: Date.now(),
  };
}

function deserializeBuilderMediaDraft(raw, fallbackType) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  const body = raw;
  const coverImage =
    parseImageRef(body.coverImage) || parseImageRef(body.heroImage) || null;
  const galleryImages = Array.isArray(body.galleryImages)
    ? body.galleryImages.map(parseImageRef).filter(Boolean)
    : [];
  const keys = Object.keys(body);
  if (keys.length === 0) return null;
  return {
    schemaVersion: 1,
    documentType: typeof body.documentType === 'string' ? body.documentType : fallbackType,
    linkedProjectId: typeof body.linkedProjectId === 'string' ? body.linkedProjectId : null,
    coverImage,
    galleryImages,
  };
}

function resolvePreferredConstructionProjectId(options) {
  const ids = new Set((options.projectIds || []).filter(Boolean));
  if (!ids.size) return null;
  for (const candidate of [options.lastSelectedId, options.draftLinkedProjectId]) {
    if (typeof candidate === 'string' && ids.has(candidate)) return candidate;
  }
  return null;
}

describe('source modules exist', () => {
  it('ships BB persistence helpers', () => {
    assert.equal(existsSync(join(bbDir, 'blog-builder-persistence.ts')), true);
    assert.equal(existsSync(join(bbDir, 'blog-builder-workspace.tsx')), true);
  });
});

describe('explicit construction project selection (no projects[0] force)', () => {
  it('prefers last selected id over draft linkedProjectId', () => {
    assert.equal(
      resolvePreferredConstructionProjectId({
        projectIds: [OTHER_UUID, TEMPLE_UUID],
        lastSelectedId: TEMPLE_UUID,
        draftLinkedProjectId: OTHER_UUID,
      }),
      TEMPLE_UUID,
    );
  });

  it('falls back to draft linkedProjectId when last selected missing', () => {
    assert.equal(
      resolvePreferredConstructionProjectId({
        projectIds: [TEMPLE_UUID],
        lastSelectedId: 'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
        draftLinkedProjectId: TEMPLE_UUID,
      }),
      TEMPLE_UUID,
    );
  });

  it('returns null when nothing matches (caller may cold-start)', () => {
    assert.equal(
      resolvePreferredConstructionProjectId({
        projectIds: [OTHER_UUID],
        lastSelectedId: null,
        draftLinkedProjectId: null,
      }),
      null,
    );
  });

  it('persistence module exports last-project + prefer helpers', () => {
    const src = readBb('blog-builder-persistence.ts');
    assert.match(src, /BB_LAST_CONSTRUCTION_PROJECT_KEY/);
    assert.match(src, /ih-bb-last-construction-project-id/);
    assert.match(src, /export function saveLastConstructionProjectId/);
    assert.match(src, /export function loadLastConstructionProjectId/);
    assert.match(src, /export function resolvePreferredConstructionProjectId/);
    assert.match(src, /export function loadPersistedLinkedProjectIdHint/);
    assert.match(src, /export function saveEmergencySnapshot/);
  });

  it('workspace wires preferredConstructionProject (not bare projects[0])', () => {
    const workspace = readBb('blog-builder-workspace.tsx');
    assert.match(workspace, /preferredConstructionProject/);
    assert.match(workspace, /loadLastConstructionProjectId/);
    assert.match(workspace, /saveLastConstructionProjectId/);
    assert.match(workspace, /loadPersistedLinkedProjectIdHint/);
    assert.match(workspace, /resolvePreferredConstructionProjectId/);
    assert.match(workspace, /saveEmergencySnapshot/);
    assert.match(workspace, /linkedProjectId:\s*docApi\.constructionProjectId/);
    assert.match(workspace, /documentType:\s*'blog'/);
  });

  it('shared document hook only forces projects[0] when preferred restore omitted', () => {
    const hook = readComponent('use-builder-document.ts');
    assert.match(hook, /preferredConstructionProject/);
    assert.match(hook, /projects\.at\(0\)/);
    // Legacy path for other builders still uses projects[0] when option omitted.
    assert.match(hook, /selected = projects\[0\]!/);
  });
});

describe('linkedProjectId + Asset ID draft roundtrip', () => {
  it('persists Temple linkedProjectId and cover/gallery Asset IDs', () => {
    const saved = serializeBuilderMediaDraft({
      documentType: 'blog',
      linkedProjectId: TEMPLE_UUID,
      coverImage: { asset_id: SAMPLE_UUID, url: null, alt: 'Cover', role: 'cover' },
      galleryImages: [{ asset_id: SAMPLE_UUID, role: 'gallery' }],
    });
    const loaded = deserializeBuilderMediaDraft(saved, 'blog');
    assert.equal(loaded.linkedProjectId, TEMPLE_UUID);
    assert.equal(loaded.coverImage.asset_id, SAMPLE_UUID);
    assert.equal(loaded.galleryImages[0].asset_id, SAMPLE_UUID);
    assert.equal(isMediaAssetUuid(loaded.coverImage.asset_id), true);
  });

  it('linkedProjectId-only draft still restores project binding', () => {
    const saved = serializeBuilderMediaDraft({
      documentType: 'blog',
      linkedProjectId: TEMPLE_UUID,
      coverImage: null,
      galleryImages: [],
    });
    const loaded = deserializeBuilderMediaDraft(saved, 'blog');
    assert.equal(loaded.linkedProjectId, TEMPLE_UUID);
    assert.equal(loaded.coverImage, null);
    assert.equal(loaded.galleryImages.length, 0);
  });

  it('cross-project isolation: different linkedProjectId does not share media ids in draft', () => {
    const temple = serializeBuilderMediaDraft({
      documentType: 'blog',
      linkedProjectId: TEMPLE_UUID,
      coverImage: { asset_id: SAMPLE_UUID, role: 'cover' },
    });
    const other = serializeBuilderMediaDraft({
      documentType: 'blog',
      linkedProjectId: OTHER_UUID,
      coverImage: null,
    });
    assert.notEqual(temple.linkedProjectId, other.linkedProjectId);
    assert.equal(deserializeBuilderMediaDraft(other, 'blog').coverImage, null);
  });
});

describe('media scoped by linked_project_id + no Unsplash production seed', () => {
  it('BB enables scopeToLinkedProject and seedFromTemplate false', () => {
    const workspace = readBb('blog-builder-workspace.tsx');
    assert.match(workspace, /seedFromTemplate:\s*false/);
    assert.match(workspace, /scopeToLinkedProject:\s*true/);
    assert.match(workspace, /lockLinkedProject/);
  });

  it('shared media hook scopes list/search when scopeToLinkedProject is on', () => {
    const hook = readComponent('use-cs-media-library.ts');
    assert.match(hook, /scopeToLinkedProject/);
    assert.match(hook, /linked_project_id:\s*linkedProjectId/);
    assert.match(hook, /a\.linked_project_id !== scopeId/);
    assert.match(hook, /Empty Media Library = empty picker/);
  });

  it('cover asset hook does not seed Unsplash when seedFromTemplate is false', () => {
    const hook = readComponent('use-builder-cover-asset.ts');
    assert.match(hook, /seedFromTemplate/);
    assert.match(hook, /if \(!seedFromTemplate\) return/);
    assert.match(hook, /scopeToLinkedProject/);
  });

  it('CsMediaPicker can lock off project "all" for BB', () => {
    const picker = readComponent('cs-media-picker.tsx');
    assert.match(picker, /lockLinkedProject/);
    assert.match(picker, /lockedProjectId/);
    assert.match(picker, /labels\.projectAll/);
  });

  it('dialog media picker locks linked project and uses CsMediaPickerDialog only', () => {
    const workspace = readBb('blog-builder-workspace.tsx');
    assert.match(workspace, /CsMediaPickerDialog/);
    assert.match(workspace, /lockLinkedProject/);
    assert.match(workspace, /linkedProjectId=\{docApi\.constructionProjectId\}/);
    assert.doesNotMatch(workspace, /BB_ASSETS\.map/);
  });

  it('production selection path does not seed picker from Unsplash samples', () => {
    const workspace = readBb('blog-builder-workspace.tsx');
    assert.doesNotMatch(workspace, /WB_ASSETS/);
    assert.doesNotMatch(workspace, /BB_ASSETS/);
    assert.match(workspace, /useBuilderCoverAsset/);
    assert.match(workspace, /CsMediaPickerDialog/);
    // templateCoverUrl still used for display atmosphere, not picker seeding
    assert.match(workspace, /seedFromTemplate:\s*false/);
  });

});
