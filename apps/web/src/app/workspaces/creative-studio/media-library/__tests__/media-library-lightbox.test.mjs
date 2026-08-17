/**
 * Media Library lightbox preview contracts.
 * Run: node --test src/app/workspaces/creative-studio/media-library/__tests__/media-library-lightbox.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const webSrc = join(here, '../../../../../');

function readRel(...parts) {
  return readFileSync(join(...parts), 'utf8');
}

const workspace = readRel(root, 'media-library-workspace.tsx');
const lightbox = readRel(root, 'media-library-lightbox.tsx');
const css = readRel(root, 'media-library.css');
const en = JSON.parse(readRel(webSrc, '../messages/en.json'));
const tr = JSON.parse(readRel(webSrc, '../messages/tr.json'));

const ML_LIGHTBOX_ZOOM_MIN = 1;
const ML_LIGHTBOX_ZOOM_MAX = 4;
const ML_LIGHTBOX_ZOOM_STEP = 0.25;

function clampLightboxZoom(zoom) {
  const rounded = Math.round(zoom * 100) / 100;
  return Math.min(ML_LIGHTBOX_ZOOM_MAX, Math.max(ML_LIGHTBOX_ZOOM_MIN, rounded));
}

function stepLightboxZoom(zoom, direction) {
  return clampLightboxZoom(zoom + direction * ML_LIGHTBOX_ZOOM_STEP);
}

function lightboxNeighborId(ids, currentId, direction) {
  const index = ids.indexOf(currentId);
  if (index < 0) return null;
  return ids[index + direction] ?? null;
}

function lightboxSourceLabel(asset, labels) {
  if (asset.sourceType === 'google_drive') return labels.googleDrive;
  return labels.uploaded;
}

describe('lightbox opens from image card click', () => {
  it('opens preview on image card activate, not on generic card chrome', () => {
    assert.match(workspace, /function handleCardActivate\(asset: MediaAsset\)/);
    assert.match(workspace, /if \(asset\.kind === 'image'\)/);
    assert.match(workspace, /setPreviewId\(asset\.id\)/);
    assert.match(workspace, /onClick=\{\(\) => handleCardActivate\(asset\)\}/);
    assert.match(workspace, /<MediaLibraryLightbox/);
    assert.match(lightbox, /<Dialog open=\{open && Boolean\(asset\)\}/);
    assert.match(lightbox, /data-testid="ml-lightbox"/);
  });
});

describe('image is contained, not cropped', () => {
  it('uses object-contain on the lightbox image and never object-cover', () => {
    assert.match(css, /\.ml-lightbox__image[\s\S]*object-fit:\s*contain/);
    assert.match(lightbox, /className="ml-lightbox__image"/);
    assert.match(lightbox, /data-testid="ml-lightbox-image"/);
    const imageBlock = css.slice(css.indexOf('.ml-lightbox__image'));
    const imageRule = imageBlock.slice(0, imageBlock.indexOf('}'));
    assert.match(imageRule, /object-fit:\s*contain/);
    assert.doesNotMatch(imageRule, /object-fit:\s*cover/);
    assert.doesNotMatch(lightbox, /object-cover|object-fit:\s*cover/);
  });
});

describe('prev / next walks the current list', () => {
  it('wires neighbor navigation and keeps buttons at list ends', () => {
    assert.match(lightbox, /export function lightboxNeighborId/);
    assert.match(lightbox, /data-testid="ml-lightbox-prev"/);
    assert.match(lightbox, /data-testid="ml-lightbox-next"/);
    assert.match(lightbox, /ArrowLeft/);
    assert.match(lightbox, /ArrowRight/);
    assert.match(workspace, /onNavigate=\{navigatePreview\}/);
    assert.match(workspace, /assetIds=\{orderedIds\}/);

    const ids = ['a', 'b', 'c'];
    assert.equal(lightboxNeighborId(ids, 'a', -1), null);
    assert.equal(lightboxNeighborId(ids, 'a', 1), 'b');
    assert.equal(lightboxNeighborId(ids, 'b', -1), 'a');
    assert.equal(lightboxNeighborId(ids, 'c', 1), null);
  });
});

describe('metadata display', () => {
  it('shows Asset ID, filename, resolution, and source', () => {
    assert.match(lightbox, /data-testid="ml-lightbox-asset-id"/);
    assert.match(lightbox, /data-testid="ml-lightbox-filename"/);
    assert.match(lightbox, /data-testid="ml-lightbox-resolution"/);
    assert.match(lightbox, /data-testid="ml-lightbox-source"/);
    assert.match(lightbox, /\{asset\.id\}/);
    assert.match(lightbox, /\{asset\.name\}/);
    assert.match(lightbox, /asset\.resolution \|\| labels\.resolutionUnavailable/);
    assert.equal(
      lightboxSourceLabel({ sourceType: 'google_drive' }, { googleDrive: 'Drive', uploaded: 'Uploaded' }),
      'Drive',
    );
    assert.equal(
      lightboxSourceLabel({ sourceType: 'upload' }, { googleDrive: 'Drive', uploaded: 'Uploaded' }),
      'Uploaded',
    );
  });
});

describe('card action buttons do not open lightbox', () => {
  it('keeps + / checkbox / favorite / more on stopPropagation', () => {
    assert.match(workspace, /onClick=\{\(e\) => openQuickTag\(asset, e\)\}/);
    assert.match(workspace, /data-testid=\{`ml-quick-tag-\$\{asset\.id\}`\}/);
    assert.match(workspace, /function openQuickTag\(asset: MediaAsset, event: MouseEvent<HTMLButtonElement>\) \{\s*event\.stopPropagation\(\);/s);
    assert.match(workspace, /function toggleFavorite\(_id: string, event: MouseEvent\) \{\s*event\.stopPropagation\(\);/s);
    assert.match(workspace, /function toggleCheck\(id: string, event: MouseEvent\) \{\s*event\.stopPropagation\(\);/s);
    assert.match(workspace, /className="ml-ws__card-more"[\s\S]*e\.stopPropagation\(\);/);
    assert.doesNotMatch(workspace, /openQuickTag\(asset, e\)[\s\S]{0,80}setPreviewId/);
  });
});

describe('zoom helpers', () => {
  it('clamps zoom and steps in 25% increments', () => {
    assert.match(lightbox, /ML_LIGHTBOX_ZOOM_MIN = 1/);
    assert.match(lightbox, /ML_LIGHTBOX_ZOOM_MAX = 4/);
    assert.match(lightbox, /data-testid="ml-lightbox-zoom-in"/);
    assert.match(lightbox, /data-testid="ml-lightbox-zoom-out"/);
    assert.equal(stepLightboxZoom(1, -1), 1);
    assert.equal(stepLightboxZoom(1, 1), 1.25);
    assert.equal(stepLightboxZoom(4, 1), 4);
    assert.equal(clampLightboxZoom(0.2), 1);
    assert.equal(clampLightboxZoom(9), 4);
  });
});

describe('i18n', () => {
  it('adds en/tr lightbox copy under Media Library', () => {
    assert.equal(en.creativeStudio.ds.mediaLibrary.lightbox.title, 'Asset preview');
    assert.equal(tr.creativeStudio.ds.mediaLibrary.lightbox.title, 'Varlık önizleme');
    assert.equal(en.creativeStudio.ds.mediaLibrary.lightbox.assetId, 'Asset ID');
    assert.equal(tr.creativeStudio.ds.mediaLibrary.lightbox.assetId, 'Varlık ID');
    assert.equal(en.creativeStudio.ds.mediaLibrary.lightbox.filename, 'Filename');
    assert.equal(tr.creativeStudio.ds.mediaLibrary.lightbox.filename, 'Dosya adı');
  });
});
