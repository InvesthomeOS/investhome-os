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

  it('finished-ad hydrate path forces sole background IMAGE without OS layers', () => {
    const helper = read('social-media-builder-gpt-image.ts');
    assert.match(helper, /createFinishedAdCanvasPost/);
    assert.match(helper, /soleFinishedImage/);
    assert.match(helper, /editable_layers: editableFinishedAd \? true : finishedAd \? false/);
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /createFinishedAdCanvasPost\(/);
    assert.doesNotMatch(
      workspace.match(/const runGenerateAdFromCampaign = useCallback\([\s\S]*?\n  \);/)?.[0] || '',
      /createDefaultElements/,
    );
  });

  it('treats golden_native_v1 as an editable finished-ad canvas without changing the default generate mode', () => {
    const helper = read('social-media-builder-gpt-image.ts');
    const workspace = read('social-media-builder-workspace.tsx');
    const api = readFileSync(apiFile, 'utf8');
    assert.match(helper, /golden_native_v1/);
    assert.match(workspace, /production_mode === 'golden_native_v1'/);
    assert.match(workspace, /production_mode: 'finished_ad'/);
    assert.match(api, /golden_native_v1/);
  });

  it('LAYER_ONLY revision keeps the selected raster cover and hydrates text overlays', () => {
    const helper = read('social-media-builder-gpt-image.ts');
    assert.match(helper, /rasterLocked/);
    assert.match(helper, /must not inject a second photograph/);
    const workspace = read('social-media-builder-workspace.tsx');
    const rev =
      workspace.match(/const runAiRevision = useCallback\([\s\S]*?\n  \);/)?.[0] || '';
    assert.match(rev, /revision_route === 'LAYER_ONLY'/);
    assert.match(rev, /lockedCoverId/);
    assert.match(rev, /localAssetId: microEditRevision \? lockedCoverId/);
    assert.match(rev, /\[SMB_REV_V3\] source/);
    assert.match(rev, /\[SMB_REV_V3\] after/);
  });

  it('renders rich headline runs when OS layers include runs', () => {
    const elements = read('social-media-builder-elements.ts');
    const artboard = read('smb-artboard-elements.tsx');
    assert.match(elements, /runs\?: SocialTextRun\[\]/);
    assert.match(artboard, /el\.runs/);
  });

  it('ensures GPT background IMAGE layer is editable separately from OS text/logo', () => {
    const helper = read('social-media-builder-gpt-image.ts');
    assert.match(helper, /ensureBackgroundLayer/);
    assert.match(helper, /background-gpt-image/);
    assert.match(helper, /role: 'background'/);
  });
});
