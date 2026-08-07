/**
 * Sprint 4 — Shared Creative Studio Media Picker contracts.
 * Run: node --test src/app/workspaces/creative-studio/_components/__tests__/cs-media-picker.test.mjs
 */

import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const componentsDir = join(here, '..');
const webSrc = join(here, '../../../../../');
const csRoot = join(here, '../..');

function read(...parts) {
  return readFileSync(join(...parts), 'utf8');
}

const DEMO_ASSET_ID_RE = /^a\d+$/i;
const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function isDemoAssetId(id) {
  return Boolean(id && DEMO_ASSET_ID_RE.test(String(id).trim()));
}

function isMediaAssetUuid(id) {
  if (!id) return false;
  const trimmed = String(id).trim();
  if (isDemoAssetId(trimmed)) return false;
  return UUID_RE.test(trimmed);
}

function getAssetSelectability(asset) {
  if (!asset?.id || isDemoAssetId(asset.id) || !isMediaAssetUuid(asset.id)) {
    return { selectable: false, reason: 'demo' };
  }
  if (asset.archived_at) return { selectable: false, reason: 'archived' };
  const sync = String(asset.sync_status || '')
    .trim()
    .toLowerCase();
  if (sync === 'missing') return { selectable: false, reason: 'missing' };
  if (sync === 'error' || sync === 'corrupted') {
    return { selectable: false, reason: 'error' };
  }
  return { selectable: true, reason: null };
}

function shouldShowInBuilderPicker(asset) {
  return !asset.archived_at;
}

const ACTIVE_ID = '11111111-1111-4111-8111-111111111111';
const MISSING_ID = '22222222-2222-4222-8222-222222222222';

describe('shared media picker modules exist', () => {
  it('ships cs-media-picker + hook + image-ref under _components', () => {
    assert.equal(existsSync(join(componentsDir, 'cs-media-picker.tsx')), true);
    assert.equal(existsSync(join(componentsDir, 'cs-media-picker-dialog.tsx')), true);
    assert.equal(existsSync(join(componentsDir, 'use-cs-media-library.ts')), true);
    assert.equal(existsSync(join(componentsDir, 'cs-image-ref.ts')), true);
    assert.equal(existsSync(join(componentsDir, 'cs-media-selectability.ts')), true);
    assert.equal(existsSync(join(componentsDir, 'use-builder-cover-asset.ts')), true);
  });

  it('exports shared picker from _components index', () => {
    const index = read(componentsDir, 'index.ts');
    assert.match(index, /CsMediaPicker/);
    assert.match(index, /CsMediaPickerDialog/);
    assert.match(index, /useCsMediaLibrary/);
    assert.match(index, /CsImageRef/);
    assert.match(index, /useBuilderCoverAsset/);
  });
});

describe('selectability rules', () => {
  it('ACTIVE uuid is selectable', () => {
    const result = getAssetSelectability({
      id: ACTIVE_ID,
      archived_at: null,
      sync_status: 'active',
    });
    assert.equal(result.selectable, true);
    assert.equal(result.reason, null);
  });

  it('MISSING is visible but not selectable', () => {
    const asset = {
      id: MISSING_ID,
      archived_at: null,
      sync_status: 'missing',
    };
    assert.equal(shouldShowInBuilderPicker(asset), true);
    const result = getAssetSelectability(asset);
    assert.equal(result.selectable, false);
    assert.equal(result.reason, 'missing');
  });

  it('archived is hidden and not selectable', () => {
    const asset = {
      id: ACTIVE_ID,
      archived_at: '2026-08-01T00:00:00Z',
      sync_status: 'active',
    };
    assert.equal(shouldShowInBuilderPicker(asset), false);
    assert.equal(getAssetSelectability(asset).selectable, false);
  });

  it('demo ids never selectable', () => {
    assert.equal(
      getAssetSelectability({ id: 'a1', archived_at: null, sync_status: 'active' }).selectable,
      false,
    );
  });

  it('mirrors TS selectability module', () => {
    const src = read(componentsDir, 'cs-media-selectability.ts');
    assert.match(src, /export function getAssetSelectability/);
    assert.match(src, /sync === 'missing'/);
    assert.match(src, /shouldShowInBuilderPicker/);
  });
});

describe('builders use shared picker / Asset IDs', () => {
  const builders = [
    ['landing-page-builder', 'landing-page-builder-workspace.tsx', 'CsMediaPicker'],
    ['blog-builder', 'blog-builder-workspace.tsx', 'CsMediaPickerDialog'],
    ['email-builder', 'email-builder-workspace.tsx', 'CsMediaPickerDialog'],
    ['proposal-builder', 'proposal-builder-workspace.tsx', 'CsMediaPickerDialog'],
    ['presentation-builder', 'presentation-builder-workspace.tsx', 'CsMediaPickerDialog'],
  ];

  for (const [dir, file, symbol] of builders) {
    it(`${dir} wires ${symbol} and cover asset hook`, () => {
      const src = read(csRoot, dir, file);
      assert.match(src, new RegExp(symbol));
      assert.match(src, /useBuilderCoverAsset/);
      assert.match(src, /coverImage|setCoverImage|coverDisplayUrl/);
      assert.doesNotMatch(src, /drive_path|drivePath|google_drive_path/);
    });
  }

  it('landing media rail embeds shared CsMediaPicker', () => {
    const rail = read(csRoot, 'landing-page-builder', 'landing-page-builder-rail-drawers.tsx');
    assert.match(rail, /CsMediaPicker/);
    assert.doesNotMatch(rail, /LPB_ASSETS\.map/);
  });

  it('website builder keeps Asset ID persistence + chooseAsset label', () => {
    const wb = read(csRoot, 'website-builder', 'website-builder-media.ts');
    assert.match(wb, /cs-image-ref/);
    assert.match(wb, /WbImageRef/);
    const rail = read(csRoot, 'website-builder', 'website-builder-rail-drawers.tsx');
    assert.match(rail, /rails\.assets\.chooseAsset/);
    const hook = read(csRoot, 'website-builder', 'use-website-builder-media.ts');
    assert.match(hook, /uploadCreativeStudioMediaAsset/);
    assert.match(hook, /!a\.archived_at/);
  });
});

describe('i18n choose asset', () => {
  it('adds mediaPicker keys in en/tr', () => {
    const en = JSON.parse(read(webSrc, '../messages/en.json'));
    const tr = JSON.parse(read(webSrc, '../messages/tr.json'));
    assert.equal(en.creativeStudio.mediaPicker.chooseAsset, 'Choose Asset');
    assert.equal(tr.creativeStudio.mediaPicker.chooseAsset, 'Varlık Seç');
    assert.equal(
      en.creativeStudio.ds.websiteBuilder.rails.assets.chooseAsset,
      'Choose Asset',
    );
  });
});

describe('no duplicated builder-owned upload ownership', () => {
  it('shared picker upload goes through Media Library API', () => {
    const picker = read(componentsDir, 'cs-media-picker.tsx');
    const hook = read(componentsDir, 'use-cs-media-library.ts');
    assert.match(hook, /uploadCreativeStudioMediaAsset/);
    assert.match(picker, /media\.uploadAsset/);
    assert.doesNotMatch(picker, /URL\.createObjectURL\(file\)/);
  });
});
