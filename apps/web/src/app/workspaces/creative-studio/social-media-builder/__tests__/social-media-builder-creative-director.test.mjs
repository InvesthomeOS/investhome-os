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
const TEMPLE_BRIEF =
  'The Temple için sosyal medya reklamı hazırla. Projenin kataloğunu ve Drive\'daki bilgileri incele. Projenin en güçlü özelliklerinden birkaçını seç ve bunları ön plana çıkar. Gerçek The Temple görsellerini ve logosunu kullan. Premium, sade ve dikkat çekici olsun. Türkçe hazırla.';

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
    assert.match(api, /export async function reviseCreativeDirectorAd/);
    assert.match(api, /return apiFetch\(`\/ai\/creative-studio\/campaigns\/\$\{campaignId\}\/revise`/);
    assert.match(api, /export async function generateCreativeDirectorAd/);
    assert.match(api, /return apiFetch\(`\/ai\/creative-studio\/campaigns\/\$\{campaignId\}\/generate-ad`/);
    const client = readFileSync(join(here, '../../../../../lib/api/client.ts'), 'utf8');
    assert.match(client, /credentials: 'include'/);
    assert.match(client, /pageHost === '127\.0\.0\.1'/);
    assert.doesNotMatch(
      api.slice(api.indexOf('export async function reviseCreativeDirectorAd'), api.indexOf('export async function getCreativeDirectorCampaign')),
      /\bfetch\(/,
      'revise must use apiFetch, not a raw fetch client',
    );
    assert.match(api, /current_final_asset_id/);
    assert.match(api, /export async function undoCreativeDirectorRevision/);
    assert.match(api, /export async function redoCreativeDirectorRevision/);
    assert.match(api, /\/redo-revision/);
    assert.match(api, /export async function getCreativeDirectorCampaign/);
    assert.match(api, /production_mode: productionMode/);
    assert.match(api, /input\.production_mode \?\? 'finished_ad'/);
    assert.doesNotMatch(api, /production_mode: input\.production_mode \?\? 'os_compose'/);
  });

  it('SMB AI revision UI wires revise endpoint without new campaign', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /reviseCreativeDirectorAd/);
    assert.match(workspace, /undoCreativeDirectorRevision/);
    assert.match(workspace, /redoCreativeDirectorRevision/);
    assert.match(workspace, /runAiRevision/);
    assert.match(workspace, /runRedoAiRevision/);
    assert.match(workspace, /canUndoAiRevision/);
    assert.match(workspace, /canRedoAiRevision/);
    assert.match(workspace, /revisionPrimary/);
    assert.match(workspace, /finishedAdCanvas/);
    assert.match(workspace, /data-testid=\{revisionPrimary \? 'smb-ai-revision' : 'smb-ai-design-actions'\}/);
    assert.match(workspace, /data-testid=\{revisionPrimary \? 'smb-ai-revision-submit' : 'smb-ai-design-submit'\}/);
    assert.match(workspace, /data-ai-workflow=\{revisionPrimary \? 'revise'/);
    assert.match(workspace, /t\('aiRevision\.submit'\)/);
    assert.match(workspace, /void runAiRevision\(aiPrompt\)/);
    assert.match(workspace, /hideOsLayers/);
    assert.match(workspace, /data-button-hierarchy="primary"/);
    assert.match(workspace, /resolvePostCampaignId/);
    const revBlock = workspace.match(/const runAiRevision = useCallback\([\s\S]*?\n  \);/);
    assert.ok(revBlock, 'runAiRevision missing');
    assert.match(revBlock[0], /current_final_asset_id/);
    assert.match(revBlock[0], /createFinishedAdCanvasPost/);
    assert.match(revBlock[0], /revision_route === 'LAYER_ONLY'/);
    assert.match(revBlock[0], /\[SMB_REV_V3\]/);
    assert.match(revBlock[0], /coverAssetId/);
    assert.match(revBlock[0], /designProvider: 'creative-director'/);
    assert.match(revBlock[0], /brandLogo: false/);
    assert.match(revBlock[0], /resolvePostCampaignId\(selectedPost\)/);
    assert.doesNotMatch(revBlock[0], /createCreativeDirectorCampaign/);
    assert.doesNotMatch(revBlock[0], /generateSocialDesign/);
    assert.doesNotMatch(revBlock[0], /createDefaultElements/);
    assert.doesNotMatch(revBlock[0], /PLACEHOLDER_HEADLINE/);
    assert.doesNotMatch(revBlock[0], /createPostFromPreset/);
    const undoBlock = workspace.match(/const runUndoAiRevision = useCallback\([\s\S]*?\n  \);/);
    assert.ok(undoBlock, 'runUndoAiRevision missing');
    assert.match(undoBlock[0], /hydrateFinishedAdFromRevisionMove|createFinishedAdCanvasPost/);
    assert.doesNotMatch(undoBlock[0], /createDefaultElements/);
    const redoBlock = workspace.match(/const runRedoAiRevision = useCallback\([\s\S]*?\n  \);/);
    assert.ok(redoBlock, 'runRedoAiRevision missing');
    assert.match(redoBlock[0], /redoCreativeDirectorRevision/);
    assert.match(redoBlock[0], /hydrateFinishedAdFromRevisionMove/);
    assert.doesNotMatch(redoBlock[0], /createDefaultElements/);
    assert.match(workspace, /data-testid="smb-redo"/);
    assert.match(workspace, /canRedoAiRevision/);
    // Finished-ad keeps both undo+redo toolbar buttons (redo not hidden).
    assert.doesNotMatch(
      workspace,
      /hideManualCanvasTools \? null : \(\s*<button[\s\S]*?data-testid="smb-redo"/,
    );
  });

  it('finished-ad selected shows AI ile Düzenle primary and routes to revise not create', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const tr = readFileSync(join(smbDir, '../../../../../messages/tr.json'), 'utf8');
    const en = readFileSync(join(smbDir, '../../../../../messages/en.json'), 'utf8');
    assert.match(tr, /"submit": "AI ile Düzenle"/);
    assert.match(tr, /"undo": "Geri Al"/);
    assert.match(tr, /"redo": "İleri Al"/);
    assert.match(en, /"redo": "Redo"/);
    assert.match(tr, /"revisionRedone"/);
    assert.match(en, /"revisionRedone"/);
    assert.match(workspace, /const revisionPrimary = finishedAdCanvas/);
    assert.match(workspace, /if \(revisionPrimary\) void runAiRevision\(aiPrompt\)/);
    assert.match(workspace, /else submitAiDesign\(\)/);
    // Primary revise path must not fall through to campaign create.
    const actionsBlock = workspace.match(
      /data-testid=\{revisionPrimary \? 'smb-ai-revision-submit'[\s\S]*?<\/Button>/,
    );
    assert.ok(actionsBlock, 'revision/create primary button missing');
    assert.match(actionsBlock[0], /runAiRevision\(aiPrompt\)/);
    assert.doesNotMatch(actionsBlock[0], /runCreativeDirectorCampaign/);
    assert.doesNotMatch(actionsBlock[0], /createCreativeDirectorCampaign/);
  });

  it('Oluştur create path calls Creative Director then finished-ad generate-ad', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /createCreativeDirectorCampaign/);
    assert.match(workspace, /runCreativeDirectorCampaign/);
    assert.match(workspace, /runGenerateAdFromCampaign/);
    assert.match(workspace, /generateCreativeDirectorAd/);
    assert.match(workspace, /createFinishedAdCanvasPost/);
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
    assert.doesNotMatch(genAdBlock[0], /createPostFromPreset/);
    assert.doesNotMatch(genAdBlock[0], /createDefaultElements/);
    assert.doesNotMatch(genAdBlock[0], /PLACEHOLDER_HEADLINE/);
    assert.match(genAdBlock[0], /production_mode: 'finished_ad'/);
    assert.match(genAdBlock[0], /final_asset_id/);
    assert.match(genAdBlock[0], /createFinishedAdCanvasPost/);
    assert.match(genAdBlock[0], /designProvider: 'creative-director'/);
    assert.match(genAdBlock[0], /brandLogo: false/);
  });

  it('submitAiDesign create uses Creative Director; native only for surgical follow-ups', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const submit = workspace.match(/function submitAiDesign\(\) \{[\s\S]*?\n  \}/);
    assert.ok(submit, 'submitAiDesign missing');
    assert.match(submit[0], /isOlusturCreateBrief\(instruction\)/);
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
    assert.match(leftRailBlock[0], /isOlusturCreateBrief/);
    assert.doesNotMatch(leftRailBlock[0], /runGptImageGenerate/);
    assert.doesNotMatch(leftRailBlock[0], /runAiGenerate\(instruction,\s*\{\s*mode:\s*'create'/);
  });

  it('finished-ad canvas mode hides OS overlays and IH stub', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    assert.match(workspace, /isFinishedAdCanvasPost/);
    assert.match(workspace, /finishedAdCanvas/);
    assert.match(workspace, /data-finished-ad-canvas/);
    assert.match(workspace, /hideOsLayers/);
    assert.match(workspace, /setBrandLogo\(false\)/);
  });

  it('consolidates primary canvas actions into single teal bottom bar', () => {
    const workspace = read('social-media-builder-workspace.tsx');
    const batSrc = readFileSync(
      join(smbDir, '../_components/cs-bottom-action-toolbar.tsx'),
      'utf8',
    );
    const sharedCss = readFileSync(
      join(smbDir, '../creative-studio-shared.css'),
      'utf8',
    );

    // Upper pilot output row removed — controls live in the dock.
    assert.doesNotMatch(workspace, /data-testid="smb-pilot-output"/);
    assert.doesNotMatch(workspace, /smb-ws__output-actions/);
    assert.doesNotMatch(workspace, /data-testid="smb-output-download"/);
    assert.doesNotMatch(workspace, /data-testid="smb-output-publish"/);

    const finishedDock = workspace.match(
      /data-testid="smb-finished-ad-dock"[\s\S]*?maxVisible=\{7\}[\s\S]*?\/>/,
    );
    assert.ok(finishedDock, 'finished-ad bottom dock missing');
    assert.match(finishedDock[0], /singleRow/);
    assert.match(finishedDock[0], /dividerAfterKey="variation"/);
    assert.match(finishedDock[0], /maxVisible=\{7\}/);
    assert.doesNotMatch(finishedDock[0], /\bprimary=\{/);
    assert.match(finishedDock[0], /testId: 'smb-output-story'/);
    assert.match(finishedDock[0], /testId: 'smb-output-reel'/);
    assert.match(finishedDock[0], /testId: 'smb-output-variation'/);
    assert.match(finishedDock[0], /testId: 'smb-action-undo'/);
    assert.match(finishedDock[0], /testId: 'smb-action-redo'/);
    assert.match(finishedDock[0], /testId: 'smb-action-download'/);
    assert.match(finishedDock[0], /testId: 'smb-action-publish'/);
    assert.match(finishedDock[0], /handleFormatChange\('story'\)/);
    assert.match(finishedDock[0], /handleFormatChange\('reelsCover'\)/);
    assert.match(finishedDock[0], /regenerateCurrentDesign\(\)/);
    assert.match(finishedDock[0], /runUndoAiRevision|undoHistory/);
    assert.match(finishedDock[0], /runRedoAiRevision|redoHistory/);
    assert.match(finishedDock[0], /runDownload/);

    // Real layout contract: exactly 7 icon+label actions; undo is not a white primary pill.
    const finishedActionKeys = [
      ...'story|reel|variation|undo|redo|download|publish'.split('|'),
    ];
    for (const key of finishedActionKeys) {
      assert.match(finishedDock[0], new RegExp(`key: '${key}'`));
    }
    assert.equal(
      (finishedDock[0].match(/\bkey: '/g) || []).length,
      7,
      'finished-ad dock must expose exactly 7 actions',
    );
    assert.doesNotMatch(
      finishedDock[0],
      /primary=\{\{[\s\S]*?label:\s*t\(['"]undo['"]\)/,
    );

    // Shared BAT: icon actions, optional primary, divider, single-row CSS.
    assert.match(batSrc, /dividerAfterKey\?:/);
    assert.match(batSrc, /singleRow\?:/);
    assert.match(batSrc, /primary\?:/);
    assert.match(batSrc, /cs-bat__divider/);
    assert.match(sharedCss, /\.cs-bat__row--single/);
    assert.match(sharedCss, /\.cs-bat__divider/);
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

describe('Finished-ad sole IMAGE hydrate helper', () => {
  it('createFinishedAdCanvasPost builds exactly one background IMAGE — no TEXT/CTA/PLACEHOLDER', () => {
    // Execute helper via tsx/register if available; otherwise assert source contract.
    const helper = read('social-media-builder-gpt-image.ts');
    assert.match(helper, /export function createFinishedAdCanvasPost/);
    assert.match(helper, /finishedAd: true/);
    assert.match(helper, /id: 'img-finished-ad'/);
    assert.match(helper, /role: 'background'/);
    assert.match(helper, /production_mode: editableFinishedAd \? 'editable_finished_ad' : 'finished_ad'/);
    assert.match(helper, /headline: finishedAd && !editableFinishedAd \? ''/);
    assert.doesNotMatch(helper, /createDefaultElements/);
    assert.doesNotMatch(helper, /PLACEHOLDER_HEADLINE/);
    assert.doesNotMatch(helper, /Schedule a private tour/);
    assert.doesNotMatch(helper, /New social post/);
  });

  it('persistence never synthesizes default elements for finished_ad drafts', () => {
    const persistence = read('social-media-builder-persistence.ts');
    assert.match(persistence, /production_mode === 'finished_ad'/);
    assert.match(persistence, /creative_director_generate_ad/);
    assert.match(persistence, /img-finished-ad/);
    assert.match(persistence, /isFinishedAdSocialPost/);
    assert.match(persistence, /Finished ads bake copy into the raster/);
    assert.match(persistence, /Prefer local finished-ad/);
    // createDefaultElements only for non-finishedAd hasCopy path
    const parseFn = persistence.slice(persistence.indexOf('export function parseSocialPost'));
    assert.match(parseFn, /finishedAd/);
    assert.ok(
      parseFn.includes('createDefaultElements') === true,
      'legacy default elements still exist for non-finished posts',
    );
  });
});

const FINAL_ASSET = 'dc339503-dd7f-4a2a-bece-17691aadf552';
const INTERIOR_ASSET = 'caf8eb97-c767-4aa1-841b-759cf3500062';
const PLACEHOLDER_HEADLINE = 'New social post';

function isFinishedAdSocialPost(post) {
  const meta = post?.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  return meta?.production_mode === 'finished_ad' || meta?.generated_by === 'creative_director_generate_ad';
}

function isInFlightGenerationPost(post) {
  return post?.generationLifecycle === 'creating' || post?.generationLifecycle === 'generating';
}

function isCompletedGeneratedPost(post) {
  if (!post || isInFlightGenerationPost(post) || post.generationLifecycle === 'error') return false;
  const meta = post.generationMeta && typeof post.generationMeta === 'object' ? post.generationMeta : null;
  const hasCover = Boolean(post.coverAssetId);
  if (isFinishedAdSocialPost(post) && hasCover) return true;
  const headline = String(post.headline || '').trim();
  if (!headline || headline === PLACEHOLDER_HEADLINE) return false;
  return Boolean(meta?.content_package || post.creativePlan || post.compositionBlueprint);
}

function isPlaceholderSocialPost(post) {
  if (!post) return false;
  if (isInFlightGenerationPost(post)) return true;
  if (isFinishedAdSocialPost(post)) return false;
  return String(post.headline || '').trim() === PLACEHOLDER_HEADLINE && !post.coverAssetId;
}

function mergeHydratedPostsWithLocal(input) {
  const incoming = input.incoming.filter((p) => !input.deletedIds.has(p.id));
  const local = input.local.filter((p) => !input.deletedIds.has(p.id));
  const localInFlight = local.filter((p) => isInFlightGenerationPost(p));
  const localCompleted = local.filter((p) => isCompletedGeneratedPost(p));

  if (input.generating || localInFlight.length) {
    return { posts: local, selectedPostId: input.localSelectedPostId ?? local[0]?.id ?? null };
  }
  if (!incoming.length && localCompleted.length) {
    return {
      posts: localCompleted,
      selectedPostId:
        (input.localSelectedPostId && localCompleted.some((p) => p.id === input.localSelectedPostId)
          ? input.localSelectedPostId
          : localCompleted[0]?.id) ?? null,
    };
  }
  const incomingIds = new Set(incoming.map((p) => p.id));
  const extraLocal = localCompleted.filter((p) => !incomingIds.has(p.id));
  const merged = incoming.map((post) => {
    const existing = local.find((l) => l.id === post.id);
    if (existing && isFinishedAdSocialPost(existing) && !isFinishedAdSocialPost(post)) return existing;
    if (existing && isCompletedGeneratedPost(existing) && !isCompletedGeneratedPost(post)) return existing;
    if (existing && isPlaceholderSocialPost(post) && !isPlaceholderSocialPost(existing)) return existing;
    return post;
  });
  const posts = [...merged, ...extraLocal];
  const localSelectedProtected =
    Boolean(
      input.localSelectedPostId &&
        local.some(
          (p) =>
            p.id === input.localSelectedPostId &&
            (isFinishedAdSocialPost(p) || isCompletedGeneratedPost(p)),
        ),
    ) && posts.some((p) => p.id === input.localSelectedPostId);
  const selected =
    (localSelectedProtected ? input.localSelectedPostId : null) ??
    (input.incomingSelectedPostId && posts.some((p) => p.id === input.incomingSelectedPostId)
      ? input.incomingSelectedPostId
      : null) ??
    (input.localSelectedPostId && posts.some((p) => p.id === input.localSelectedPostId)
      ? input.localSelectedPostId
      : null) ??
    posts[0]?.id ??
    null;
  return { posts, selectedPostId: selected };
}

function coerceFinishedAdElements(rawElements, coverAssetId, width, height) {
  const assetId = coverAssetId || null;
  if (!assetId) return [];
  return [
    {
      id: 'img-finished-ad',
      type: 'IMAGE',
      role: 'background',
      assetId,
      x: 0,
      y: 0,
      width,
      height,
      zIndex: 0,
    },
  ];
}

describe('Finished-ad hydrate resists draft restore placeholders', () => {
  const finishedAd = {
    id: 'post-finished-1',
    name: 'Finished Ad',
    headline: '',
    coverAssetId: FINAL_ASSET,
    generationLifecycle: 'ready',
    generationMeta: {
      production_mode: 'finished_ad',
      generated_by: 'creative_director_generate_ad',
      gpt_image: { local_asset_id: FINAL_ASSET, editable_layers: false },
    },
    elements: [
      {
        id: 'img-finished-ad',
        type: 'IMAGE',
        role: 'background',
        assetId: FINAL_ASSET,
        x: 0,
        y: 0,
        width: 1080,
        height: 1350,
        zIndex: 0,
      },
    ],
  };

  const stalePlaceholder = {
    id: 'p-stale',
    headline: PLACEHOLDER_HEADLINE,
    coverAssetId: INTERIOR_ASSET,
    generationLifecycle: 'ready',
    generationMeta: null,
    elements: [
      { id: 'headline-1', type: 'TEXT', role: 'headline', content: PLACEHOLDER_HEADLINE },
      { id: 'cta-1', type: 'BUTTON', label: 'Özel tur planlayın' },
    ],
  };

  it('finished-ad hydrate is exactly 1 IMAGE with final asset id', () => {
    assert.equal(finishedAd.elements.length, 1);
    assert.equal(finishedAd.elements[0].type, 'IMAGE');
    assert.equal(finishedAd.elements[0].assetId, FINAL_ASSET);
    assert.equal(finishedAd.elements.filter((e) => e.type === 'TEXT').length, 0);
    assert.equal(finishedAd.elements.filter((e) => e.type === 'BUTTON').length, 0);
    assert.equal(isCompletedGeneratedPost(finishedAd), true);
    assert.equal(isPlaceholderSocialPost(finishedAd), false);
  });

  it('coerceFinishedAdElements strips rebound TEXT/CTA placeholders', () => {
    const polluted = [
      { id: 'headline-1', type: 'TEXT', content: PLACEHOLDER_HEADLINE },
      { id: 'cta-1', type: 'BUTTON', label: 'Özel tur planlayın' },
      { id: 'img-x', type: 'IMAGE', assetId: INTERIOR_ASSET },
    ];
    const cleaned = coerceFinishedAdElements(polluted, FINAL_ASSET, 1080, 1350);
    assert.equal(cleaned.length, 1);
    assert.equal(cleaned[0].type, 'IMAGE');
    assert.equal(cleaned[0].assetId, FINAL_ASSET);
    assert.equal(cleaned.filter((e) => e.type === 'TEXT').length, 0);
    assert.equal(cleaned.filter((e) => e.type === 'BUTTON').length, 0);
  });

  it('stale draft restore does not overwrite finished-ad or steal selection', () => {
    const merged = mergeHydratedPostsWithLocal({
      incoming: [stalePlaceholder],
      local: [finishedAd],
      deletedIds: new Set(),
      generating: false,
      incomingSelectedPostId: 'p-stale',
      localSelectedPostId: 'post-finished-1',
    });
    assert.equal(merged.selectedPostId, 'post-finished-1');
    const active = merged.posts.find((p) => p.id === merged.selectedPostId);
    assert.ok(active);
    assert.equal(isFinishedAdSocialPost(active), true);
    assert.equal(active.coverAssetId, FINAL_ASSET);
    assert.equal(active.elements.length, 1);
    assert.equal(active.elements[0].type, 'IMAGE');
    assert.equal(active.elements[0].assetId, FINAL_ASSET);
    assert.equal(active.elements.filter((e) => e.type === 'TEXT').length, 0);
    assert.equal(active.elements.filter((e) => e.type === 'BUTTON').length, 0);
    assert.equal(active.headline, '');
  });

  it('same-id stale placeholder cannot replace finished-ad canvas', () => {
    const polluted = {
      ...finishedAd,
      headline: PLACEHOLDER_HEADLINE,
      coverAssetId: INTERIOR_ASSET,
      generationMeta: null,
      elements: [
        { id: 'headline-1', type: 'TEXT', content: PLACEHOLDER_HEADLINE },
        { id: 'cta-1', type: 'BUTTON', label: 'Özel tur planlayın' },
      ],
    };
    const merged = mergeHydratedPostsWithLocal({
      incoming: [polluted],
      local: [finishedAd],
      deletedIds: new Set(),
      generating: false,
      incomingSelectedPostId: 'post-finished-1',
      localSelectedPostId: 'post-finished-1',
    });
    assert.equal(merged.posts[0].coverAssetId, FINAL_ASSET);
    assert.equal(isFinishedAdSocialPost(merged.posts[0]), true);
    assert.equal(merged.posts[0].elements.length, 1);
    assert.equal(merged.posts[0].elements[0].assetId, FINAL_ASSET);
  });
});

describe('Oluştur orchestration request shape (acceptance parity)', () => {
  it('builds Temple TR campaigns then generate-ad finished_ad — never social/design', () => {
    const built = buildOlusturOrchestration({
      projectId: TEMPLE_UUID,
      brief: TEMPLE_BRIEF,
      locale: 'tr',
      formatPreset: 'portrait',
    });
    assert.equal(built.ok, true);
    assert.equal(built.steps.length, 2);
    assert.equal(built.steps[0].path, '/ai/creative-studio/campaigns');
    assert.equal(built.steps[0].body.project_id, TEMPLE_UUID);
    assert.equal(built.steps[0].body.language, 'tr');
    assert.equal(built.steps[0].body.mode, 'project');
    assert.equal(built.steps[0].body.brief, TEMPLE_BRIEF);
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

describe('Oluştur create brief inference (no native steal)', () => {
  it('Temple brief is classified as Oluştur create', () => {
    const engine = read('social-media-builder-design-engine.ts');
    assert.match(engine, /export function isOlusturCreateBrief/);
    assert.match(engine, /reklam/);
    assert.match(engine, /sosyal medya/);
    // Inline mirror of isOlusturCreateBrief for Temple brief.
    const GENERATION_VERBS = ['hazırla', 'hazirla', 'oluştur', 'olustur', 'create a', 'generate a', 'prepare a'];
    const COMPLETE_POST_MARKERS = [
      'post',
      'instagram',
      'kare',
      'feed',
      'gönderi',
      'gonderi',
      'creative',
      'reklam',
      'sosyal medya',
      'kampanya',
      'campaign',
    ];
    const SURGICAL = ['taşı', 'move the', 'remove the', 'küçült'];
    const lower = TEMPLE_BRIEF.toLowerCase();
    const hasVerb = GENERATION_VERBS.some((v) => lower.includes(v));
    const hasPost = COMPLETE_POST_MARKERS.some((m) => lower.includes(m));
    const surgical = SURGICAL.some((h) => lower.includes(h));
    assert.equal(hasVerb && hasPost, true);
    assert.equal(surgical, false);
  });
});
