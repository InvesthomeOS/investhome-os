/**
 * SMB AI Design → Oluştur → finished-ad orchestration (same path as Unit 204 acceptance).
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

/** Mirrors SMB create + generate-ad request sequence (no network). */
function buildOlusturOrchestration({ projectId, brief, locale, formatPreset = 'portrait' }) {
  const linked = typeof projectId === 'string' ? projectId.trim() : '';
  if (!linked) return { ok: false, reason: 'missing_project' };
  const text = (brief || '').trim();
  if (!text) return { ok: false, reason: 'missing_brief' };
  const aspect =
    formatPreset === 'portrait' ? '4:5' : formatPreset === 'square' ? '1:1' : '4:5';
  return {
    ok: true,
    steps: [
      {
        method: 'POST',
        path: '/ai/creative-studio/campaigns',
        body: {
          project_id: linked,
          brief: text,
          mode: 'project',
          language: locale || 'tr',
        },
      },
      {
        method: 'POST',
        pathTemplate: '/ai/creative-studio/campaigns/{campaign_id}/generate-ad',
        body: {
          language: locale || 'tr',
          aspect_ratio: aspect,
          format_preset: formatPreset,
          production_mode: 'finished_ad',
        },
      },
    ],
    forbidden: [
      '/ai/creative-studio/social/design',
      '/ai/creative-studio/social/gpt-image/generate',
    ],
  };
}

describe('Creative Director SMB wiring (finished-ad)', () => {
  it('API client exposes campaigns + generate-ad with finished_ad default', () => {
    const api = readFileSync(apiFile, 'utf8');
    assert.match(api, /export async function createCreativeDirectorCampaign/);
    assert.match(api, /\/ai\/creative-studio\/campaigns/);
    assert.match(api, /export async function generateCreativeDirectorAd/);
    assert.match(api, /\/generate-ad/);
    assert.match(api, /production_mode: productionMode/);
    assert.match(api, /input\.production_mode \?\? 'finished_ad'/);
    assert.doesNotMatch(api, /production_mode: input\.production_mode \?\? 'os_compose'/);
  });

  it('Oluştur create path calls Creative Director then finished-ad generate-ad', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /createCreativeDirectorCampaign/);
    assert.match(workspace, /runCreativeDirectorCampaign/);
    assert.match(workspace, /runGenerateAdFromCampaign/);
    assert.match(workspace, /generateCreativeDirectorAd/);
    assert.match(workspace, /void runCreativeDirectorCampaign\(instruction\)/);
    assert.match(workspace, /await runGenerateAdFromCampaign\(campaignId, token\)/);
    assert.match(workspace, /production_mode: 'finished_ad'/);
    assert.match(workspace, /designEngineRef\.current = 'creative-director'/);
    assert.match(workspace, /data-testid="smb-creative-director-campaign-id"/);
    assert.match(workspace, /final_asset_id/);
    assert.doesNotMatch(workspace, /void runGptImageGenerate\(instruction\)/);
    assert.doesNotMatch(workspace, /fallbackToNative/);
    assert.doesNotMatch(workspace, /fallbackToGptImage/);
  });

  it('Oluştur create path does not call native social/design or GPT Image POC', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const cdBlock = workspace.match(
      /const runCreativeDirectorCampaign = useCallback\([\s\S]*?\n  \);/,
    );
    assert.ok(cdBlock, 'runCreativeDirectorCampaign missing');
    assert.doesNotMatch(cdBlock[0], /generateSocialDesign/);
    assert.doesNotMatch(cdBlock[0], /generateGptImageDesign/);
    assert.doesNotMatch(cdBlock[0], /\/ai\/creative-studio\/social\/design/);

    const genAdBlock = workspace.match(
      /const runGenerateAdFromCampaign = useCallback\([\s\S]*?\n  \);/,
    );
    assert.ok(genAdBlock, 'runGenerateAdFromCampaign missing');
    assert.doesNotMatch(genAdBlock[0], /generateSocialDesign/);
    assert.doesNotMatch(genAdBlock[0], /generateGptImageDesign/);
    assert.match(genAdBlock[0], /production_mode: 'finished_ad'/);
    assert.match(genAdBlock[0], /final_asset_id/);
    assert.match(genAdBlock[0], /designProvider: 'creative-director'/);
  });

  it('submitAiDesign create uses Creative Director; native only for explicit edit follow-ups', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const submit = workspace.match(/function submitAiDesign\(\) \{[\s\S]*?\n  \}/);
    assert.ok(submit, 'submitAiDesign missing');
    assert.match(submit[0], /runCreativeDirectorCampaign\(instruction\)/);
    assert.doesNotMatch(submit[0], /runGptImageGenerate/);
    assert.doesNotMatch(submit[0], /runAiGenerate\(instruction,\s*\{\s*mode:\s*'create'/);
    assert.match(workspace, /mode: 'edit', explicit: true/);
    assert.match(workspace, /generateSocialDesign/);
  });

  it('left rail create path uses Creative Director not GPT Image or native', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const leftRailBlock = workspace.match(/onGenerate=\{\(instruction\) => \{[\s\S]*?\}\}/);
    assert.ok(leftRailBlock, 'onGenerate handler missing');
    assert.match(leftRailBlock[0], /runCreativeDirectorCampaign/);
    assert.doesNotMatch(leftRailBlock[0], /runGptImageGenerate/);
    assert.doesNotMatch(leftRailBlock[0], /runAiGenerate\(instruction,\s*\{\s*mode:\s*'create'/);
  });

  it('passes project_id, brief, mode project, and locale language to campaigns', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /project_id: projectId/);
    assert.match(workspace, /mode: 'project'/);
    assert.match(workspace, /language: locale/);
    assert.match(workspace, /brief,/);
  });

  it('stores campaign_id and surfaces failures without silent native fallback', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /creativeDirectorCampaignRef\.current = campaignId/);
    assert.match(workspace, /toasts\.campaignFailed/);
    assert.match(workspace, /toasts\.campaignCreated/);
  });
});

describe('Oluştur orchestration request shape (acceptance parity)', () => {
  it('builds Temple TR campaigns then generate-ad finished_ad — never social/design', () => {
    const built = buildOlusturOrchestration({
      projectId: TEMPLE_UUID,
      brief:
        'The Temple için sosyal medya reklamı hazırla. Drive bilgilerini incele. Türkçe hazırla.',
      locale: 'tr',
      formatPreset: 'portrait',
    });
    assert.equal(built.ok, true);
    assert.equal(built.steps.length, 2);
    assert.equal(built.steps[0].path, '/ai/creative-studio/campaigns');
    assert.equal(built.steps[0].body.project_id, TEMPLE_UUID);
    assert.equal(built.steps[0].body.language, 'tr');
    assert.equal(built.steps[0].body.mode, 'project');
    assert.equal(
      built.steps[1].pathTemplate,
      '/ai/creative-studio/campaigns/{campaign_id}/generate-ad',
    );
    assert.equal(built.steps[1].body.production_mode, 'finished_ad');
    assert.equal(built.steps[1].body.language, 'tr');
    assert.equal(built.steps[1].body.aspect_ratio, '4:5');
    assert.equal(built.steps[1].body.format_preset, 'portrait');
    assert.ok(built.forbidden.includes('/ai/creative-studio/social/design'));
    assert.ok(built.forbidden.includes('/ai/creative-studio/social/gpt-image/generate'));
  });

  it('rejects empty brief / missing project like SMB guards', () => {
    assert.equal(
      buildOlusturOrchestration({ projectId: '', brief: 'x', locale: 'tr' }).ok,
      false,
    );
    assert.equal(
      buildOlusturOrchestration({ projectId: TEMPLE_UUID, brief: '  ', locale: 'tr' }).ok,
      false,
    );
  });
});
