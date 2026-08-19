/**
 * SMB AI Design → Creative Director campaign wiring (Phase 1 — no GPT Image).
 * Run: node --test src/app/workspaces/creative-studio/social-media-builder/__tests__/social-media-builder-creative-director.test.mjs
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

const TEMPLE_UUID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

describe('Creative Director SMB wiring (Phase 1)', () => {
  it('adds campaigns endpoint on the API client', () => {
    const api = readFileSync(apiFile, 'utf8');
    assert.match(api, /export async function createCreativeDirectorCampaign/);
    assert.match(api, /\/ai\/creative-studio\/campaigns/);
    assert.match(api, /CreativeDirectorCampaignRequest/);
    assert.match(api, /CreativeDirectorCampaignResponse/);
  });

  it('Oluştur create path calls Creative Director — not native design', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /createCreativeDirectorCampaign/);
    assert.match(workspace, /runCreativeDirectorCampaign/);
    assert.match(workspace, /void runCreativeDirectorCampaign\(instruction\)/);
    assert.match(workspace, /designEngineRef\.current = 'creative-director'/);
    assert.match(workspace, /data-testid="smb-creative-director-campaign-id"/);
    assert.match(workspace, /setCreativeDirectorCampaignId/);
    assert.doesNotMatch(workspace, /void runGptImageGenerate\(instruction\)/);
    assert.doesNotMatch(workspace, /fallbackToNative/);
    assert.doesNotMatch(workspace, /fallbackToGptImage/);
  });

  it('passes project_id, brief, mode project, and locale language to campaigns', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /project_id: projectId/);
    assert.match(workspace, /mode: 'project'/);
    assert.match(workspace, /language: locale/);
    assert.match(workspace, /brief,/);
  });

  it('stores a new campaign_id per brief without silent native fallback on failure', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /creativeDirectorCampaignRef\.current = campaignId/);
    assert.match(workspace, /toasts\.campaignFailed/);
    assert.match(workspace, /toasts\.campaignCreated/);
    const cdBlock = workspace.match(
      /const runCreativeDirectorCampaign = useCallback\([\s\S]*?\n  \);/,
    );
    assert.ok(cdBlock, 'runCreativeDirectorCampaign missing');
    assert.doesNotMatch(cdBlock[0], /generateSocialDesign/);
    assert.doesNotMatch(cdBlock[0], /generateGptImageDesign/);
  });

  it('keeps native design only for explicit edit follow-ups', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /mode: 'edit', explicit: true/);
    assert.match(workspace, /generateSocialDesign/);
    assert.match(workspace, /canFollowUp/);
  });

  it('left rail create path uses Creative Director not GPT Image', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const leftRailBlock = workspace.match(/onGenerate=\{\(instruction\) => \{[\s\S]*?\}\}/);
    assert.ok(leftRailBlock, 'onGenerate handler missing');
    assert.match(leftRailBlock[0], /runCreativeDirectorCampaign/);
    assert.doesNotMatch(leftRailBlock[0], /runGptImageGenerate/);
  });

  it('generate-ad hydrates SMB canvas from campaign master ad', () => {
    const api = readFileSync(apiFile, 'utf8');
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(api, /generateCreativeDirectorAd/);
    assert.match(api, /\/generate-ad/);
    assert.match(workspace, /runGenerateAdFromCampaign/);
    assert.match(workspace, /generateCreativeDirectorAd/);
    assert.match(workspace, /createFlattenedGptImagePost/);
    assert.doesNotMatch(workspace, /generateSocialDesign\([\s\S]*runGenerateAdFromCampaign/);
  });
});

describe('Creative Director request shape (inlined mirror)', () => {
  function buildCampaignRequest({ projectId, brief, locale }) {
    const linked = typeof projectId === 'string' ? projectId.trim() : '';
    if (!linked) return { ok: false, reason: 'missing_project' };
    const text = (brief || '').trim();
    if (!text) return { ok: false, reason: 'missing_brief' };
    return {
      ok: true,
      request: {
        project_id: linked,
        brief: text,
        mode: 'project',
        language: locale || 'tr',
      },
    };
  }

  it('builds Temple TR campaign request from Turkish brief', () => {
    const built = buildCampaignRequest({
      projectId: TEMPLE_UUID,
      brief: 'The Temple için premium bir sosyal medya reklamı hazırla. Türkçe çalış.',
      locale: 'tr',
    });
    assert.equal(built.ok, true);
    assert.equal(built.request.project_id, TEMPLE_UUID);
    assert.equal(built.request.language, 'tr');
    assert.equal(built.request.mode, 'project');
  });
});
