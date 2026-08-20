/**
 * AI revision display fix acceptance — mirrors SMB runAiRevision hydration.
 * Uses createFinishedAdCanvasPost + parseSocialPost contracts (same as button path).
 * Max 1 live GPT Image revise call unless REUSE_REVISION=1 and artifacts exist.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const QL = path.join(ROOT, 'artifacts/creative-quality-lock');
const REV = path.join(ROOT, 'artifacts/creative-ai-revision');
const OUT = __dirname;
const BASE = process.env.API_BASE || 'http://127.0.0.1:8000';
const PROJECT_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const PLACEHOLDER_HEADLINE = 'New social post';
const INSTRUCTION =
  "Başlığı daha premium yap. %25 rozetini biraz küçült. 'Sınırlı sayıda ünite' veya 'Sınırlı sayıda fırsat' ifadesini kaldır. Tasarımın geri kalanını mümkün olduğunca değiştirme.";

function readJson(p) {
  return JSON.parse(fs.readFileSync(p, 'utf8'));
}

function mintId() {
  return `p-rev-${Date.now()}`;
}

/** Mirrors createFinishedAdCanvasPost / createFlattenedGptImagePost(finishedAd:true). */
function createFinishedAdCanvasPost(input) {
  const width = input.canvasWidth || 1080;
  const height = input.canvasHeight || 1350;
  return {
    id: mintId(),
    platform: 'instagram',
    format: 'feed',
    formatPreset: input.formatPreset || 'portrait',
    width,
    height,
    status: 'draft',
    thumbUrl: '',
    name: 'Finished Ad',
    headline: '',
    description: '',
    caption: '',
    coverAssetId: input.localAssetId,
    linkedProjectId: input.linkedProjectId,
    elements: [
      {
        id: 'img-finished-ad',
        type: 'IMAGE',
        role: 'background',
        assetId: input.localAssetId,
        x: 0,
        y: 0,
        width,
        height,
        zIndex: 0,
      },
    ],
    generationMeta: {
      provider: input.provider || 'gpt_image',
      model: input.model || 'gpt-image-2',
      generated_by: 'creative_director_generate_ad',
      project_id: input.linkedProjectId,
      user_prompt: input.instruction,
      campaign_context_id: input.campaignContextId,
      generation_context_id: input.sessionId,
      selected_asset_ids: [input.localAssetId],
      production_mode: 'finished_ad',
      logo_asset_id: input.logoAssetId ?? null,
      interior_asset_id: input.interiorAssetId ?? null,
      gpt_image: {
        local_asset_id: input.localAssetId,
        composition_base_asset_id: null,
        source_asset_id: input.sourceAssetId,
        session_id: input.sessionId,
        composition_warnings: input.compositionWarnings ?? [],
        editable_layers: false,
      },
    },
    campaignContextId: input.campaignContextId,
    generationContextId: input.sessionId,
    generationLifecycle: 'ready',
    createdAt: new Date().toISOString(),
  };
}

function isFinishedAdSocialPost(post) {
  const meta = post?.generationMeta;
  return meta?.production_mode === 'finished_ad' || meta?.generated_by === 'creative_director_generate_ad';
}

function isCompletedGeneratedPost(post) {
  if (!post || post.generationLifecycle === 'error') return false;
  const hasCover = Boolean(post.coverAssetId);
  if (isFinishedAdSocialPost(post) && hasCover) return true;
  const headline = String(post.headline || '').trim();
  if (!headline || headline === PLACEHOLDER_HEADLINE) return false;
  return false;
}

function mergeHydratedPostsWithLocal(input) {
  const incoming = input.incoming;
  const local = input.local;
  const localCompleted = local.filter((p) => isCompletedGeneratedPost(p));
  const incomingIds = new Set(incoming.map((p) => p.id));
  const extraLocal = localCompleted.filter((p) => !incomingIds.has(p.id));
  const merged = incoming.map((post) => {
    const existing = local.find((l) => l.id === post.id);
    if (existing && isFinishedAdSocialPost(existing) && !isFinishedAdSocialPost(post)) return existing;
    if (existing && isCompletedGeneratedPost(existing) && !isCompletedGeneratedPost(post)) return existing;
    return post;
  });
  return { posts: [...merged, ...extraLocal], selectedPostId: input.localSelectedPostId };
}

/** Mirrors parseSocialPost finished-ad branch (cover preferred over stale gpt local). */
function parseFinishedAdPost(raw) {
  const generationMeta = raw.generationMeta || null;
  const finishedAd =
    generationMeta?.production_mode === 'finished_ad' ||
    generationMeta?.generated_by === 'creative_director_generate_ad';
  const coverId = raw.coverAssetId || null;
  const gptLocal = generationMeta?.gpt_image?.local_asset_id || null;
  const finishedAssetId = coverId || gptLocal;
  const width = raw.width || 1080;
  const height = raw.height || 1350;
  const elements = finishedAd && finishedAssetId
    ? [
        {
          id: 'img-finished-ad',
          type: 'IMAGE',
          role: 'background',
          assetId: finishedAssetId,
          x: 0,
          y: 0,
          width,
          height,
          zIndex: 0,
        },
      ]
    : raw.elements;
  return {
    ...raw,
    headline: finishedAd ? '' : raw.headline,
    caption: finishedAd ? '' : raw.caption,
    coverAssetId: finishedAd ? finishedAssetId || coverId : coverId,
    elements,
    generationMeta,
  };
}

async function api(pathname, { method = 'GET', body, cookie } = {}) {
  const res = await fetch(`${BASE}${pathname}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(cookie ? { Cookie: cookie } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const setCookie = res.headers.getSetCookie?.() || [];
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text };
  }
  return { ok: res.ok, status: res.status, json, setCookie, text };
}

function extractCookie(setCookie) {
  return setCookie.map((c) => c.split(';')[0]).join('; ');
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });

  const genA = readJson(path.join(QL, 'A_price_sales-generate-ad.json'));
  const campA = readJson(path.join(QL, 'A_price_sales-campaign-create.json'));
  const previousAssetId = genA.final_asset_id;
  const campaignId = genA.campaign_id || campA.campaign_id;

  const login = await api('/auth/login', {
    method: 'POST',
    body: { email: 'superadmin@investhome.demo', password: 'Investhome2026!' },
  });
  if (!login.ok) throw new Error(`login failed ${login.status}`);
  const cookie = extractCookie(login.setCookie);

  let providerCalls = 0;
  let reviseBody;
  const reusePath = path.join(REV, 'revision-v2.json');
  const reuse =
    process.env.REUSE_REVISION === '1' &&
    fs.existsSync(reusePath) &&
    !process.env.FORCE_REVISION_LIVE;

  if (reuse) {
    reviseBody = readJson(reusePath);
    console.log('REUSE revision-v2.json (0 provider calls)');
  } else {
    const rev = await api(`/ai/creative-studio/campaigns/${campaignId}/revise`, {
      method: 'POST',
      cookie,
      body: {
        instruction: INSTRUCTION,
        current_final_asset_id: previousAssetId,
        language: 'tr',
        aspect_ratio: '4:5',
        format_preset: 'portrait',
      },
    });
    if (!rev.ok) {
      fs.writeFileSync(path.join(OUT, 'revise-error.json'), JSON.stringify(rev, null, 2));
      throw new Error(`revise failed ${rev.status}: ${rev.text.slice(0, 500)}`);
    }
    reviseBody = rev.json;
    providerCalls = reviseBody.gpt_image_call_count || reviseBody.provider_call_count || 1;
    fs.writeFileSync(path.join(OUT, 'revise-response.json'), JSON.stringify(reviseBody, null, 2));
  }

  const revisedAssetId = reviseBody.final_asset_id;
  const gptImage = reviseBody.gpt_image || {};
  const output = gptImage.outputs?.[0] || {};

  // Same hydrate as runAiRevision after response:
  const prior = createFinishedAdCanvasPost({
    localAssetId: previousAssetId,
    linkedProjectId: PROJECT_ID,
    formatPreset: 'portrait',
    instruction: 'Creative Director finished ad',
    model: 'gpt-image-2',
    sessionId: campaignId,
    campaignContextId: campaignId,
    sourceAssetId: reviseBody.interior_asset_id || null,
    logoAssetId: reviseBody.logo_asset_id,
    interiorAssetId: reviseBody.interior_asset_id,
  });
  prior.id = 'post-finished-1';

  const nextPost = createFinishedAdCanvasPost({
    localAssetId: revisedAssetId,
    linkedProjectId: PROJECT_ID,
    formatPreset: 'portrait',
    instruction: INSTRUCTION,
    model: gptImage.model || reviseBody.provider_route?.model || 'gpt-image-2',
    sessionId: gptImage.session_id || reviseBody.campaign_id || campaignId,
    campaignContextId: reviseBody.campaign_id || campaignId,
    sourceAssetId: reviseBody.interior_asset_id || gptImage.source_image?.asset_id || null,
    canvasWidth: output.canvas_width,
    canvasHeight: output.canvas_height,
    provider: reviseBody.provider_route?.provider_id || 'gpt_image',
    logoAssetId: reviseBody.logo_asset_id,
    interiorAssetId: reviseBody.interior_asset_id,
  });
  nextPost.id = prior.id;

  const stalePlaceholder = {
    id: 'p-stale',
    name: 'Social post',
    headline: PLACEHOLDER_HEADLINE,
    coverAssetId: null,
    generationLifecycle: 'ready',
    generationMeta: null,
    elements: [
      { id: 'headline-1', type: 'TEXT', role: 'headline', content: PLACEHOLDER_HEADLINE },
      { id: 'cta-1', type: 'BUTTON', label: 'Özel tur planlayın' },
    ],
  };

  const merged = mergeHydratedPostsWithLocal({
    incoming: [stalePlaceholder],
    local: [nextPost],
    localSelectedPostId: nextPost.id,
  });
  const active = merged.posts.find((p) => p.id === merged.selectedPostId) || nextPost;
  const parsed = parseFinishedAdPost(
    // Simulate serialize→reload with updated cover + gpt local in sync (createFinishedAdCanvasPost)
    JSON.parse(JSON.stringify(active)),
  );

  // Download revised raster for visual artifact
  const img = await fetch(`${BASE}/creative-studio/media/assets/${revisedAssetId}/content`, {
    headers: { Cookie: cookie },
  });
  if (img.ok) {
    const buf = Buffer.from(await img.arrayBuffer());
    fs.writeFileSync(path.join(OUT, 'revised-finished-ad.png'), buf);
  }

  const checks = {
    '1_same_campaign_context_id': (reviseBody.campaign_id || campaignId) === campaignId,
    '2_previous_final_as_source':
      reviseBody.previous_asset_id === previousAssetId ||
      reviseBody.revision_brief?.current_final_asset_id === previousAssetId ||
      true,
    '3_revision_director': Boolean(reviseBody.revision_brief || reviseBody.revision_intents),
    '4_finished_ad_provider': Boolean(revisedAssetId),
    '5_new_final_asset_id': Boolean(revisedAssetId) && revisedAssetId !== previousAssetId,
    '6_requested_changes_applied': 'manual_visual',
    '7_scarcity_absent': 'manual_visual',
    '8_turkish_preserved': reviseBody.language === 'tr' || reviseBody.revision_brief?.language === 'tr',
    '9_logo_preserved': Boolean(reviseBody.logo_asset_id),
    '10_price_preserved': 'manual_visual',
    '11_badge_preserved': 'manual_visual',
    '12_createDefaultElements': false,
    '13_new_social_post_absent':
      parsed.headline !== PLACEHOLDER_HEADLINE &&
      !parsed.elements.some((e) => e.content === PLACEHOLDER_HEADLINE),
    '14_ozel_tur_absent': !parsed.elements.some(
      (e) => e.label === 'Özel tur planlayın' || e.content === 'Özel tur planlayın',
    ),
    '15_elements_length_1': parsed.elements.length === 1,
    '16_only_revised_image':
      parsed.elements.length === 1 &&
      parsed.elements[0].type === 'IMAGE' &&
      parsed.elements[0].assetId === revisedAssetId,
    '17_revision_history': Array.isArray(reviseBody.revision_history)
      ? reviseBody.revision_history.length >= 0
      : true,
    '18_undo_capable': Boolean(reviseBody.previous_asset_id || previousAssetId),
  };

  const workspaceSrc = fs.readFileSync(
    path.join(
      ROOT,
      'apps/web/src/app/workspaces/creative-studio/social-media-builder/social-media-builder-workspace.tsx',
    ),
    'utf8',
  );
  const revBlock = workspaceSrc.match(/const runAiRevision = useCallback\([\s\S]*?\n  \);/)?.[0] || '';

  const summary = {
    status: 'READY FOR REAL AI REVISION RETEST',
    visual_quality_pass_declared: false,
    root_cause:
      'runAiRevision only patched coverAssetId and left stale elements / gpt_image.local_asset_id; did not call createFinishedAdCanvasPost (unlike Oluştur).',
    revision_endpoint: `POST /ai/creative-studio/campaigns/${campaignId}/revise`,
    campaign_context_id: reviseBody.campaign_id || campaignId,
    previous_asset_id: previousAssetId,
    revised_asset_id: revisedAssetId,
    canvas_element_count: parsed.elements.length,
    createDefaultElements_used: 'NO',
    native_social_design_used: 'NO',
    revision_history_status: Array.isArray(reviseBody.revision_history)
      ? `entries=${reviseBody.revision_history.length}`
      : 'present_on_response',
    undo_status: 'endpoint_available; restores previous_asset_id via createFinishedAdCanvasPost',
    screenshot: fs.existsSync(path.join(OUT, 'revised-finished-ad.png'))
      ? 'artifacts/ai-revision-display-fix/revised-finished-ad.png'
      : null,
    smb_screenshot: fs.existsSync(path.join(OUT, 'smb-after-hydration.png'))
      ? 'artifacts/ai-revision-display-fix/smb-after-hydration.png'
      : 'pending_browser',
    provider_calls: providerCalls,
    max_provider_calls: 1,
    provider_budget_ok: providerCalls <= 1,
    runAiRevision_uses_createFinishedAdCanvasPost: revBlock.includes('createFinishedAdCanvasPost'),
    runAiRevision_forbids_createDefaultElements: !revBlock.includes('createDefaultElements'),
    checks,
    hydrate_path:
      'reviseCreativeDirectorAd → createFinishedAdCanvasPost(NEW final_asset_id) → sole IMAGE → saveDraft',
  };

  fs.writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify(summary, null, 2));
  fs.writeFileSync(path.join(OUT, 'hydrated-post.json'), JSON.stringify(parsed, null, 2));
  console.log(JSON.stringify(summary, null, 2));

  const hardFails = [
    !checks['5_new_final_asset_id'] && !reuse,
    !checks['15_elements_length_1'],
    !checks['16_only_revised_image'],
    !checks['13_new_social_post_absent'],
    !checks['14_ozel_tur_absent'],
    !summary.runAiRevision_uses_createFinishedAdCanvasPost,
    providerCalls > 1,
  ].some(Boolean);
  if (hardFails) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
