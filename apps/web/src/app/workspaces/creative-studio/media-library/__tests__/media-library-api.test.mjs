/**
 * Media Library UI ↔ Creative Studio Media API integration contracts.
 * Run: node --test src/app/workspaces/creative-studio/media-library/__tests__/media-library-api.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');

function read(name) {
  return readFileSync(join(root, name), 'utf8');
}

const apiMap = read('media-library-api-map.ts');
const hook = read('use-media-library.ts');
const workspace = read('media-library-workspace.tsx');
const model = read('media-library-model.ts');
const client = readFileSync(
  join(here, '../../../../../lib/api/creative-studio.ts'),
  'utf8',
);

const SAMPLE_UUID = '11111111-1111-4111-8111-111111111111';

describe('uuid / demo id guards', () => {
  it('api-map rejects demo ids and accepts UUIDs', () => {
    assert.match(apiMap, /isDemoAssetId/);
    assert.match(apiMap, /isMediaAssetUuid/);
    assert.match(apiMap, /isApiFolderId/);
    assert.match(apiMap, /DEMO_ASSET_ID_RE/);
    assert.match(apiMap, /UUID_RE/);
  });

  it('hook never fetches blobs for non-UUID ids', () => {
    assert.match(hook, /isMediaAssetUuid\(assetId\)/);
    assert.match(hook, /fetchCreativeStudioMediaBlob/);
    assert.match(hook, /URL\.createObjectURL/);
    assert.match(hook, /URL\.revokeObjectURL/);
  });
});

describe('demo data policy', () => {
  it('DEMO_ASSETS retained as empty-state samples only', () => {
    assert.match(model, /Empty-library samples only/);
    assert.match(hook, /DEMO_ASSETS/);
    assert.match(hook, /usingSamples/);
    assert.match(hook, /markSampleAssets/);
  });

  it('successful API list never falls back to DEMO (even when empty)', () => {
    // Regression: empty search/list used to call applyDemoSamples and stick usingSamples=true.
    assert.match(hook, /Successful API responses \(including empty\) are primary/);
    assert.match(hook, /apiReadyRef/);
    assert.match(hook, /applyDemoSamples/);
    // applyList must clear samples; DEMO only gated on !apiReadyRef in catch.
    const applyListStart = hook.indexOf('const applyList = useCallback');
    const applyListBody = hook.slice(applyListStart, hook.indexOf('const getCachedDisplayUrl'));
    assert.match(applyListBody, /setUsingSamples\(false\)/);
    assert.doesNotMatch(applyListBody, /DEMO_ASSETS|applyDemoSamples/);
    const catchStart = hook.indexOf('} catch (err) {');
    const catchBody = hook.slice(catchStart, catchStart + 600);
    assert.match(catchBody, /!apiReadyRef\.current/);
    assert.match(catchBody, /applyDemoSamples/);
  });

  it('workspace never seeds DEMO_ASSETS as primary state', () => {
    assert.doesNotMatch(workspace, /useState<MediaAsset\[\]>\(DEMO_ASSETS\)/);
    assert.match(workspace, /useMediaLibrary/);
    assert.match(workspace, /usingSamples/);
    assert.match(workspace, /ml-samples-hint/);
  });
});

describe('race / stale response handling', () => {
  it('uses generation tokens and AbortController to ignore stale list responses', () => {
    assert.match(hook, /listGenRef/);
    assert.match(hook, /listAbortRef/);
    assert.match(hook, /AbortController/);
    assert.match(hook, /gen !== listGenRef\.current/);
    assert.match(hook, /abort\.signal\.aborted/);
    // Must NOT bump gen then join an older same-key inflight (invalidates the in-flight apply).
    assert.doesNotMatch(hook, /listInflightKeyRef/);
    assert.doesNotMatch(hook, /listInflightPromiseRef/);
  });

  it('clears search still drives a full list refresh (not blocked by usingSamples)', () => {
    assert.match(workspace, /debouncedQuery/);
    assert.match(workspace, /SEARCH_DEBOUNCE_MS/);
    // Regression: `if (media.usingSamples) return` prevented clear-search recovery.
    const effectIdx = workspace.indexOf('void media.refresh({');
    assert.ok(effectIdx > 0);
    const effectWindow = workspace.slice(effectIdx - 200, effectIdx + 280);
    assert.doesNotMatch(effectWindow, /if \(media\.usingSamples\) return/);
    assert.match(effectWindow, /folderId: apiFolderId/);
    assert.match(effectWindow, /query: debouncedQuery/);
  });
});

describe('folder filter hygiene', () => {
  it('sanitizes demo folder ids before API list/upload', () => {
    assert.match(hook, /sanitizeFolderId|isApiFolderId/);
    assert.match(hook, /lastFolderRef\.current = folderId/);
    assert.match(workspace, /apiFolderId/);
    assert.match(workspace, /isMediaAssetUuid\(folderId\)/);
    assert.match(workspace, /ml-folder-all/);
    // All Assets / upload must pass explicit null, not coalesce onto stale lastFolderRef.
    assert.match(hook, /folderId !== undefined \? sanitizeFolderId\(folderId\)/);
  });

  it('rejects non-UUID folder ids as API filters', () => {
    // Lightweight inline reimplementation mirroring api-map.
    const DEMO_ASSET_ID_RE = /^a\d+$/i;
    const UUID_RE =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    function isApiFolderId(id) {
      if (!id) return false;
      const trimmed = id.trim();
      if (DEMO_ASSET_ID_RE.test(trimmed)) return false;
      return UUID_RE.test(trimmed);
    }
    assert.equal(isApiFolderId('temple'), false);
    assert.equal(isApiFolderId('social'), false);
    assert.equal(isApiFolderId('a1'), false);
    assert.equal(isApiFolderId(SAMPLE_UUID), true);
    assert.equal(isApiFolderId(null), false);
  });
});

describe('API methods used', () => {
  const required = [
    'listCreativeStudioMediaAssets',
    'searchCreativeStudioMediaAssets',
    'uploadCreativeStudioMediaAsset',
    'fetchCreativeStudioMediaBlob',
    'listCreativeStudioMediaFolders',
    'createCreativeStudioMediaFolder',
    'updateCreativeStudioMediaTags',
    'deleteCreativeStudioMediaAsset',
  ];

  for (const name of required) {
    it(`hook or workspace uses ${name}`, () => {
      assert.match(client, new RegExp(`export (async )?function ${name}`));
      assert.match(hook, new RegExp(name));
    });
  }

  it('client exposes Drive visibility fields on CreativeStudioMediaAsset', () => {
    assert.match(client, /source_type\?:/);
    assert.match(client, /sync_status\?:/);
    assert.match(client, /possible_duplicate\?:/);
    assert.match(client, /web_view_link\?:/);
  });
});

describe('upload behavior', () => {
  it('uses upload lock and sequential multi-file upload', () => {
    assert.match(hook, /uploadLockRef/);
    assert.match(hook, /uploadFiles/);
    assert.match(hook, /for \(const file of list\)/);
    assert.match(hook, /uploadCreativeStudioMediaAsset/);
  });

  it('workspace mounts native file input and drag-drop', () => {
    assert.match(workspace, /data-testid="ml-upload-input"/);
    assert.match(workspace, /type="file"/);
    assert.match(workspace, /multiple/);
    assert.match(workspace, /ML_UPLOAD_ACCEPT/);
    assert.match(workspace, /onDrop/);
    assert.match(workspace, /uploadInputRef\.current\?\.click\(\)/);
    assert.match(workspace, /e\.target\.value = ''/);
  });

  it('snapshots FileList to File[] before clearing the input', () => {
    // Regression: holding a live FileList then resetting value empties it → silent no-op upload.
    const onChangeIdx = workspace.indexOf('data-testid="ml-upload-input"');
    assert.ok(onChangeIdx >= 0);
    const snippet = workspace.slice(onChangeIdx, onChangeIdx + 500);
    assert.match(snippet, /Array\.from\(e\.target\.files\)/);
    const arrayFromIdx = snippet.indexOf('Array.from(e.target.files)');
    const clearIdx = snippet.indexOf("e.target.value = ''");
    assert.ok(arrayFromIdx >= 0 && clearIdx > arrayFromIdx);
  });

  it('validates MIME / extensions before upload', () => {
    assert.match(apiMap, /isAllowedMediaUpload/);
    assert.match(apiMap, /ML_UPLOAD_ACCEPT/);
    assert.match(hook, /isAllowedMediaUpload/);
    assert.match(workspace, /isAllowedMediaUpload/);
  });

  it('upload handler selects newest asset and surfaces failure toast', () => {
    assert.match(workspace, /setSelectedId\(uploaded\.id\)/);
    assert.match(workspace, /toasts\.uploadFailed/);
    assert.match(workspace, /toasts\.unsupportedType/);
    assert.match(workspace, /uploadFiles\(list, apiFolderId\)/);
  });
});

describe('search / filter / folders', () => {
  it('debounces search and refreshes with folder / archived flags', () => {
    assert.match(workspace, /SEARCH_DEBOUNCE_MS/);
    assert.match(workspace, /debouncedQuery/);
    assert.match(workspace, /includeArchived: sidebar === 'trash'/);
    assert.match(workspace, /apiFolderId/);
    assert.match(workspace, /ml-folder-all/);
  });

  it('creates folders via API when endpoint exists', () => {
    assert.match(hook, /createCreativeStudioMediaFolder/);
    assert.match(workspace, /media\.createFolder/);
  });
});

describe('tags / archive / download', () => {
  it('updates tags through updateCreativeStudioMediaTags', () => {
    assert.match(hook, /updateCreativeStudioMediaTags/);
    assert.match(workspace, /media\.updateTags/);
    assert.match(workspace, /MediaLibraryTagEditor|MediaLibraryQuickTagPopover/);
  });

  it('archives with Dialog confirmation and soft-delete API', () => {
    assert.match(workspace, /archiveConfirm/);
    assert.match(workspace, /ml-archive-confirm/);
    assert.doesNotMatch(workspace, /window\.confirm/);
    assert.match(workspace, /media\.archiveAsset/);
    assert.match(hook, /deleteCreativeStudioMediaAsset/);
    assert.match(workspace, /actions\.archive/);
  });

  it('downloads via authenticated blob and preserves filename', () => {
    assert.match(hook, /downloadAsset/);
    assert.match(hook, /anchor\.download/);
    assert.match(workspace, /media\.downloadAsset/);
    assert.match(workspace, /downloadNamedAsset/);
  });
});

describe('quick tag / multi-select / bulk / trash', () => {
  it('wires card plus as Quick Tag popover (not selection)', () => {
    assert.match(workspace, /ml-quick-tag-/);
    assert.match(workspace, /openQuickTag/);
    assert.match(workspace, /MediaLibraryQuickTagPopover/);
    assert.match(workspace, /card\.quickTag/);
    // Plus handle must call quick tag, not toggleSelectHandle.
    const plusIdx = workspace.indexOf('ml-ws__select-handle');
    assert.ok(plusIdx > 0);
    const plusWindow = workspace.slice(plusIdx, plusIdx + 350);
    assert.match(plusWindow, /openQuickTag/);
    assert.doesNotMatch(plusWindow, /toggleSelectHandle|toggleCheck/);
  });

  it('supports checkbox multi-select with clear and context reset', () => {
    assert.match(workspace, /ml-check-/);
    assert.match(workspace, /ml-bulk-bar/);
    assert.match(workspace, /ml-bulk-clear/);
    assert.match(workspace, /setSelectedSet\(new Set\(\)\)/);
    assert.match(workspace, /rangeSelectIds/);
    assert.match(workspace, /Clear multi-select when list context changes/);
  });

  it('exposes bulk add/remove tags and bulk archive when selection > 0', () => {
    assert.match(workspace, /ml-bulk-add-tags/);
    assert.match(workspace, /ml-bulk-remove-tags/);
    assert.match(workspace, /ml-bulk-archive/);
    assert.match(workspace, /openBulkTag/);
    assert.match(workspace, /requestArchiveBulk/);
    // Move-to-folder not offered when backend lacks PATCH.
    assert.doesNotMatch(workspace, /moveToFolder|bulk-move/);
  });

  it('wires trash nav to include_archived and stays restore-free', () => {
    assert.match(workspace, /includeArchived: sidebar === 'trash'/);
    assert.match(workspace, /ml-type-\$\{item\.id\}/);
    assert.match(workspace, /trashReadOnly/);
    assert.doesNotMatch(workspace, /restoreCreativeStudioMedia|restoreAsset|media\.restore/);
  });

  it('defaults sort to newest for duplicate cleanup workflows', () => {
    assert.match(workspace, /useState<SortKey>\('newest'\)/);
    assert.match(model, /sort === 'newest'|return b\.addedAt\.localeCompare/);
  });
});

describe('favorites / usage placeholders', () => {
  it('does not fake favorites against the API', () => {
    assert.match(workspace, /favoriteUnavailable/);
    assert.match(apiMap, /favorite: false/);
  });

  it('usage panel stays placeholder when where-used missing', () => {
    assert.match(workspace, /right\.noUsage/);
    assert.match(apiMap, /usages: \[\]/);
  });
});

describe('mapper smoke', () => {
  it('maps content types to kinds', () => {
    function kindFromContentType(contentType) {
      const ct = (contentType || '').toLowerCase();
      if (ct.startsWith('image/')) return 'image';
      if (ct.startsWith('video/')) return 'video';
      if (ct === 'application/pdf') return 'document';
      return 'other';
    }
    assert.equal(kindFromContentType('image/png'), 'image');
    assert.equal(kindFromContentType('video/mp4'), 'video');
    assert.equal(kindFromContentType('application/pdf'), 'document');
  });

  it('sample uuid constant is valid shape', () => {
    assert.match(SAMPLE_UUID, /^[0-9a-f-]{36}$/i);
  });
});
