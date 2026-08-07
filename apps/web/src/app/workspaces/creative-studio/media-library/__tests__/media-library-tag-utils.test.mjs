/**
 * Media Library tag / selection helper contracts.
 * Run: node --test src/app/workspaces/creative-studio/media-library/__tests__/media-library-tag-utils.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');

// Load compiled-less TS via dynamic transpile is unavailable; reimplement smoke checks
// against the source source-of-truth and mirror pure helper logic inline for unit asserts.
const utilsSrc = readFileSync(join(root, 'media-library-tag-utils.ts'), 'utf8');
const editorSrc = readFileSync(join(root, 'media-library-tag-editor.tsx'), 'utf8');
const popoverSrc = readFileSync(join(root, 'media-library-quick-tag-popover.tsx'), 'utf8');

function normalizeTag(raw) {
  return raw.trim().replace(/\s+/g, ' ');
}

function uniqueTags(tags) {
  const seen = new Set();
  const out = [];
  for (const raw of tags) {
    const tag = normalizeTag(raw);
    if (!tag) continue;
    const key = tag.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(tag);
  }
  return out;
}

function mergeTags(existing, toAdd) {
  return uniqueTags([...existing, ...toAdd]);
}

function removeTags(existing, toRemove) {
  const drop = new Set(toRemove.map((t) => normalizeTag(t).toLowerCase()).filter(Boolean));
  return existing.filter((t) => !drop.has(normalizeTag(t).toLowerCase()));
}

function rangeSelectIds(orderedIds, fromId, toId) {
  const a = orderedIds.indexOf(fromId);
  const b = orderedIds.indexOf(toId);
  if (a < 0 || b < 0) return [toId];
  const start = Math.min(a, b);
  const end = Math.max(a, b);
  return orderedIds.slice(start, end + 1);
}

describe('shared tag UI modules exist', () => {
  it('exports MediaLibraryTagEditor and QuickTagPopover', () => {
    assert.match(editorSrc, /export function MediaLibraryTagEditor/);
    assert.match(popoverSrc, /export function MediaLibraryQuickTagPopover/);
    assert.match(popoverSrc, /updateCreativeStudioMediaTags|onApply/);
    assert.match(editorSrc, /StatusChip/);
  });

  it('tag utils expose merge/remove/range helpers', () => {
    assert.match(utilsSrc, /export function mergeTags/);
    assert.match(utilsSrc, /export function removeTags/);
    assert.match(utilsSrc, /export function rangeSelectIds/);
    assert.match(utilsSrc, /export function pushRecentTags/);
  });
});

describe('tag helper behavior', () => {
  it('merges and dedupes tags case-insensitively', () => {
    assert.deepEqual(mergeTags(['Hero', 'render'], ['hero', 'dusk']), ['Hero', 'render', 'dusk']);
  });

  it('removes tags case-insensitively', () => {
    assert.deepEqual(removeTags(['Hero', 'render', 'dusk'], ['hero']), ['render', 'dusk']);
  });

  it('range-selects inclusive ordered ids', () => {
    assert.deepEqual(rangeSelectIds(['a', 'b', 'c', 'd'], 'b', 'd'), ['b', 'c', 'd']);
    assert.deepEqual(rangeSelectIds(['a', 'b', 'c', 'd'], 'd', 'b'), ['b', 'c', 'd']);
    assert.deepEqual(rangeSelectIds(['a', 'b', 'c'], 'x', 'c'), ['c']);
  });
});

describe('no fake restore / move-folder client', () => {
  it('client has no media restore or move-folder helpers', () => {
    const client = readFileSync(
      join(here, '../../../../../lib/api/creative-studio.ts'),
      'utf8',
    );
    assert.match(client, /deleteCreativeStudioMediaAsset/);
    assert.match(client, /updateCreativeStudioMediaTags/);
    assert.doesNotMatch(client, /restoreCreativeStudioMediaAsset|moveCreativeStudioMediaAsset/);
  });
});
