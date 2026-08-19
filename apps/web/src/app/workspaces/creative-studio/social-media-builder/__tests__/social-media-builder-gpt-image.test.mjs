/**
 * GPT Image SMB wiring — Native/Ideogram remain available; create uses GPT Image.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-gpt-image.test.mjs
 */

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it } from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const smbDir = join(here, '..');
const apiFile = join(here, '../../../../../lib/api/creative-studio.ts');

function read(name) {
  return readFileSync(join(smbDir, name), 'utf8');
}

describe('GPT Image SMB wiring', () => {
  it('keeps GPT Image path available without using it for AI Design Oluştur create', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /generateGptImageDesign/);
    assert.match(workspace, /runGptImageGenerate/);
    assert.match(workspace, /runCreativeDirectorCampaign/);
    assert.match(workspace, /createCreativeDirectorCampaign/);
    assert.doesNotMatch(workspace, /void runGptImageGenerate\(instruction\)/);
    assert.doesNotMatch(workspace, /fallbackToNative/);
    assert.doesNotMatch(workspace, /fallbackToIdeogram/);
  });

  it('keeps GPT Image HTTP on the API client', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const api = readFileSync(apiFile, 'utf8');
    assert.doesNotMatch(workspace, /api\.openai\.com/);
    assert.match(api, /\/ai\/creative-studio\/social\/gpt-image\/generate/);
    assert.match(api, /\/ai\/creative-studio\/social\/gpt-image\/status/);
  });

  it('maps OS composition layers onto the SMB canvas when present', () => {
    const helper = read('social-media-builder-gpt-image.ts');
    assert.match(helper, /compositionBaseAssetId/);
    assert.match(helper, /editable_layers/);
    assert.match(helper, /asSocialElements/);
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /output\.layers/);
    assert.match(workspace, /composition_base_asset_id/);
  });
});
