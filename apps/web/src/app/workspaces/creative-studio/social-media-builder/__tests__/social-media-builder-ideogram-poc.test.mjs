/**
 * Ideogram POC UI wiring — Native SMB remains the default engine.
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-ideogram-poc.test.mjs
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

describe('Ideogram POC wiring', () => {
  it('keeps Ideogram generate path without exposing engine names in the AI prompt UI', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.doesNotMatch(workspace, /smb-ai-engine-selector/);
    assert.doesNotMatch(workspace, /smb-ai-engine-native/);
    assert.doesNotMatch(workspace, /smb-ai-engine-ideogram/);
    assert.match(workspace, /generateIdeogramDesign/);
    assert.match(workspace, /generateSocialDesign/);
    assert.match(workspace, /smb-ai-design-submit/);
    assert.match(workspace, /designEngineRef\.current === 'ideogram'/);
    assert.match(workspace, /design_provider: 'ideogram'/);
    assert.match(workspace, /designProvider: 'native'/);
    assert.match(workspace, /createFlattenedIdeogramPost/);
    assert.doesNotMatch(workspace, /fallbackToNative/);
  });

  it('keeps Ideogram HTTP on the API client, not in React fetch-to-ideogram', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const api = readFileSync(apiFile, 'utf8');
    assert.doesNotMatch(workspace, /api\.ideogram\.ai/);
    assert.match(api, /\/ai\/creative-studio\/social\/ideogram\/generate/);
    assert.match(api, /\/ai\/creative-studio\/social\/ideogram\/status/);
    assert.match(api, /design_provider: 'ideogram'/);
    assert.match(api, /design_provider: input\.design_provider \?\? 'native'/);
  });

  it('creates flattened posts from selected Ideogram output', () => {
    const helper = read('social-media-builder-ideogram-poc.ts');
    assert.match(helper, /createFlattenedIdeogramPost/);
    assert.match(helper, /formatPreset: 'square'/);
    assert.match(helper, /provider: 'ideogram'/);
    assert.match(helper, /type: 'IMAGE'/);
  });
});
