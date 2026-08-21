/**
 * Social Media Builder production project + media wiring.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-persistence.test.mjs
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
  it('ships SMB persistence helpers', () => {
    assert.equal(existsSync(join(smbDir, 'social-media-builder-persistence.ts')), true);
    assert.equal(existsSync(join(smbDir, 'social-media-builder-workspace.tsx')), true);
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

  it('round-trips compositionBlueprint without recomputing layout', () => {
    const src = readSmb('social-media-builder-persistence.ts');
    assert.match(src, /compositionBlueprint/);
    assert.match(src, /compositionFamily/);
    assert.match(src, /composition_blueprint/);
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /data-composition-family/);
    const engine = readSmb('social-media-builder-design-engine.ts');
    assert.match(engine, /composition_blueprint/);
  });

  it('persistence module exports last-project + prefer helpers', () => {
    const src = readSmb('social-media-builder-persistence.ts');
    assert.match(src, /SMB_LAST_CONSTRUCTION_PROJECT_KEY/);
    assert.match(src, /ih-smb-last-construction-project-id/);
    assert.match(src, /export function saveLastConstructionProjectId/);
    assert.match(src, /export function loadLastConstructionProjectId/);
    assert.match(src, /export function resolvePreferredConstructionProjectId/);
    assert.match(src, /export function loadPersistedLinkedProjectIdHint/);
    assert.match(src, /export function saveEmergencySnapshot/);
  });

  it('workspace wires preferredConstructionProject (not bare projects[0])', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /preferredConstructionProject/);
    assert.match(workspace, /loadLastConstructionProjectId/);
    assert.match(workspace, /saveLastConstructionProjectId/);
    assert.match(workspace, /loadPersistedLinkedProjectIdHint/);
    assert.match(workspace, /resolvePreferredConstructionProjectId/);
    assert.match(workspace, /saveEmergencySnapshot/);
    assert.match(workspace, /linkedProjectId:\s*docApi\.constructionProjectId/);
    assert.match(workspace, /documentType:\s*'social'/);
    assert.doesNotMatch(workspace, /setProjectId/);
    assert.doesNotMatch(workspace, /ProjectId\s*=\s*'temple'/);
    assert.doesNotMatch(workspace, /value=\{projectId\}/);
  });

  it('shared document hook only forces projects[0] when preferred restore omitted', () => {
    const hook = readComponent('use-builder-document.ts');
    assert.match(hook, /preferredConstructionProject/);
    assert.match(hook, /projects\.at\(0\)/);
    // Legacy path for other builders still uses projects[0] when option omitted.
    assert.match(hook, /selected = projects\[0\]!/);
  });

  it('shared BuilderMediaDocumentType includes social', () => {
    const persistence = readComponent('builder-media-persistence.ts');
    assert.match(persistence, /\| 'social'/);
    assert.match(persistence, /social:\s*'Social'/);
    assert.match(persistence, /'social'/);
  });
});

describe('linkedProjectId + Asset ID draft roundtrip', () => {
  it('persists Temple linkedProjectId and cover/gallery Asset IDs', () => {
    const saved = serializeBuilderMediaDraft({
      documentType: 'social',
      linkedProjectId: TEMPLE_UUID,
      coverImage: { asset_id: SAMPLE_UUID, url: null, alt: 'Cover', role: 'cover' },
      galleryImages: [{ asset_id: SAMPLE_UUID, role: 'gallery' }],
    });
    const loaded = deserializeBuilderMediaDraft(saved, 'social');
    assert.equal(loaded.linkedProjectId, TEMPLE_UUID);
    assert.equal(loaded.coverImage.asset_id, SAMPLE_UUID);
    assert.equal(loaded.galleryImages[0].asset_id, SAMPLE_UUID);
    assert.equal(isMediaAssetUuid(loaded.coverImage.asset_id), true);
  });

  it('linkedProjectId-only draft still restores project binding', () => {
    const saved = serializeBuilderMediaDraft({
      documentType: 'social',
      linkedProjectId: TEMPLE_UUID,
      coverImage: null,
      galleryImages: [],
    });
    const loaded = deserializeBuilderMediaDraft(saved, 'social');
    assert.equal(loaded.linkedProjectId, TEMPLE_UUID);
    assert.equal(loaded.coverImage, null);
    assert.equal(loaded.galleryImages.length, 0);
  });

  it('cross-project isolation: different linkedProjectId does not share media ids in draft', () => {
    const temple = serializeBuilderMediaDraft({
      documentType: 'social',
      linkedProjectId: TEMPLE_UUID,
      coverImage: { asset_id: SAMPLE_UUID, role: 'cover' },
    });
    const other = serializeBuilderMediaDraft({
      documentType: 'social',
      linkedProjectId: OTHER_UUID,
      coverImage: null,
    });
    assert.notEqual(temple.linkedProjectId, other.linkedProjectId);
    assert.equal(deserializeBuilderMediaDraft(other, 'social').coverImage, null);
  });
});

describe('media scoped by linked_project_id + no Unsplash production seed', () => {
  it('SMB enables scopeToLinkedProject and seedFromTemplate false', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
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

  it('CsMediaPicker can lock off project "all" for SMB', () => {
    const picker = readComponent('cs-media-picker.tsx');
    assert.match(picker, /lockLinkedProject/);
    assert.match(picker, /lockedProjectId/);
    assert.match(picker, /labels\.projectAll/);
  });

  it('dialog media picker locks linked project and uses CsMediaPickerDialog only', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /CsMediaPickerDialog/);
    assert.match(workspace, /lockLinkedProject/);
    assert.match(workspace, /linkedProjectId=\{docApi\.constructionProjectId\}/);
    assert.doesNotMatch(workspace, /SMB_ASSETS\.map/);
  });

  it('MediaDrawer is the only picker entry for insert; replace uses CsMediaPicker', () => {
    const rail = readSmb('social-media-builder-rail-drawers.tsx');
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(rail, /onOpenMediaPicker/);
    assert.match(rail, /smb-media-open-picker/);
    assert.match(workspace, /onOpenMediaPicker=\{\(\) => coverAsset\.openPicker\('cover'\)\}/);
    // Floating canvas toolbar must be gone — edits live in the right panel.
    assert.doesNotMatch(workspace, /data-testid="smb-floating-actions"/);
    assert.doesNotMatch(workspace, /smb-ws__format-tabs/);
    assert.match(workspace, /smb-replace-media-picker-dialog/);
    assert.doesNotMatch(workspace, /data-testid="smb-floating-more"/);
  });

  it('Content change-image and bottom image open CsMediaPicker', () => {
    const rail = readSmb('social-media-builder-rail-drawers.tsx');
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(rail, /onChangeImage/);
    assert.match(rail, /smb-content-change-image/);
    assert.match(workspace, /onChangeBackground=\{\(\) => coverAsset\.openPicker\('cover'\)\}/);
    assert.match(workspace, /action === 'image'/);
    assert.match(workspace, /setElementImagePickerOpen\(true\)/);
  });

  it('Sil clears cover Asset ID and persists via saveDraft', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /function handleDeleteSelectedElement/);
    assert.match(workspace, /coverAsset\.clearCover\(\)/);
    assert.match(workspace, /coverImage:\s*null/);
    assert.match(workspace, /toasts\.imageRemoved/);
  });

  it('preview uses focus mode without toast-only success', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /focus\.setMode\('preview'\)/);
    const previewBlock = workspace.match(
      /data-testid="smb-preview"[\s\S]*?\{t\('preview'\)\}/,
    );
    assert.ok(previewBlock, 'expected preview button');
    assert.doesNotMatch(previewBlock[0], /toasts\.preview/);
  });

  it('download exports real PNG via exportSocialPostPng', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /exportSocialPostPng/);
    assert.match(workspace, /runDownload/);
    assert.match(workspace, /toasts\.downloadFailed/);
    assert.equal(existsSync(join(smbDir, 'social-media-builder-export.ts')), true);
    const exportSrc = readSmb('social-media-builder-export.ts');
    assert.match(exportSrc, /canvas\.toBlob/);
    assert.match(exportSrc, /No image to export/);
  });

  it('artboard uses authenticated cover blob only — no Unsplash fallback', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /useSmbPostAssetHydration/);
    assert.match(workspace, /postAssets\.artboardSrc/);
    assert.match(workspace, /smb-artboard-empty|smb-artboard-error/);
    assert.match(workspace, /data-image-state=\{displayArtboardState\}/);
    assert.doesNotMatch(
      workspace,
      /artboardSrc\s*=\s*coverAsset\.coverDisplayUrl\s*\|\|\s*selectedPost\.thumbUrl\s*\|\|\s*project\.coverUrl/,
    );
    assert.doesNotMatch(workspace, /unsplash\.com/);
  });

  it('cover hook exposes coverStatus and skips template fallback when seedFromTemplate false', () => {
    const hook = readComponent('use-builder-cover-asset.ts');
    assert.match(hook, /coverStatus/);
    assert.match(hook, /CoverResolveStatus/);
    assert.match(hook, /Asset-backed slot: never fall back to template/);
  });

  it('media blob fetch passes linked_project_id when scoped', () => {
    const hook = readComponent('use-cs-media-library.ts');
    assert.match(hook, /fetchCreativeStudioMediaBlob\(assetId,\s*\{/);
    assert.match(hook, /linked_project_id:\s*scopeId/);
  });

  it('production selection path does not seed picker from Unsplash samples', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.doesNotMatch(workspace, /WB_ASSETS/);
    assert.doesNotMatch(workspace, /SMB_ASSETS/);
    assert.match(workspace, /useBuilderCoverAsset/);
    assert.match(workspace, /CsMediaPickerDialog/);
    assert.match(workspace, /seedFromTemplate:\s*false/);
  });

  it('workspace Select uses construction project UUIDs not temple/309h slugs', () => {
    const workspace = readSmb('social-media-builder-workspace.tsx');
    assert.match(workspace, /docApi\.constructionProjects\.map/);
    assert.match(workspace, /p\.project_name/);
    assert.doesNotMatch(workspace, /SMB_PROJECTS\.map/);
    assert.doesNotMatch(workspace, /as ProjectId/);
  });
});
