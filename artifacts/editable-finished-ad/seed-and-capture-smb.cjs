/**
 * Seed SMB draft with live editable_finished_ad post, then screenshot artboard + dock.
 */
const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve('artifacts/editable-finished-ad');
const BASE = process.env.WEB_BASE || 'http://localhost:3000';
const API = process.env.API_BASE || 'http://localhost:8000';
const TEMPLE = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

async function api(pathname, { method = 'GET', body, cookie } = {}) {
  const res = await fetch(`${API}${pathname}`, {
    method,
    headers: {
      'content-type': 'application/json',
      ...(cookie ? { cookie } : {}),
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
  if (!res.ok) {
    throw new Error(`${method} ${pathname} → ${res.status} ${text.slice(0, 400)}`);
  }
  return { json, setCookie, cookieHeader: setCookie.map((c) => c.split(';')[0]).join('; ') };
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const gen = JSON.parse(fs.readFileSync(path.join(OUT, 'generate-ad-response.json'), 'utf8'));
  const reviseD = fs.existsSync(path.join(OUT, 'revise-D.json'))
    ? JSON.parse(fs.readFileSync(path.join(OUT, 'revise-D.json'), 'utf8'))
    : gen;

  const login = await api('/auth/login', {
    method: 'POST',
    body: { email: 'superadmin@investhome.demo', password: 'Investhome2026!' },
  });
  let cookie = login.cookieHeader;
  // httpx/fetch may not always expose set-cookie the same way — also try cookie jar from playwright later.

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();

  await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"]').first().fill('Investhome2026!');
  await Promise.all([
    page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 60000 }),
    page.locator('button[type="submit"]').click(),
  ]);

  // Use browser cookies for API draft seed
  const cookies = await context.cookies(API);
  cookie = cookies.map((c) => `${c.name}=${c.value}`).join('; ');

  const docs = await api(`/creative-studio/projects?linked_project_id=${TEMPLE}`, { cookie });
  // Fallback list
  let csProjectId = null;
  let list = Array.isArray(docs.json) ? docs.json : docs.json?.items || docs.json?.projects || [];
  if (!list.length) {
    // try documents bootstrap path used by SMB
    const alt = await api(`/creative-studio/projects`, { cookie });
    list = Array.isArray(alt.json) ? alt.json : alt.json?.items || [];
  }
  const match = list.find(
    (p) =>
      String(p.linked_project_id || p.construction_project_id || '') === TEMPLE ||
      /temple/i.test(String(p.name || '')),
  );
  csProjectId = match?.id || list[0]?.id;
  if (!csProjectId) throw new Error('No creative studio project for Temple');

  const documents = await api(`/creative-studio/projects/${csProjectId}/documents?document_type=social`, {
    cookie,
  });
  let docList = Array.isArray(documents.json) ? documents.json : documents.json?.items || [];
  let documentId = docList[0]?.id;
  if (!documentId) {
    const created = await api(`/creative-studio/projects/${csProjectId}/documents`, {
      method: 'POST',
      cookie,
      body: { document_type: 'social', title: 'Editable Finished Ad Seed' },
    });
    documentId = created.json.id;
  }

  const canvas = reviseD.design_spec?.canvas || gen.design_spec?.canvas || { width: 1080, height: 1350 };
  const layers = reviseD.editable_layers || gen.editable_layers || [];
  const masterBg =
    reviseD.master_background_asset_id ||
    gen.master_background_asset_id ||
    gen.interior_asset_id;
  const postId = `p-editable-${Date.now()}`;
  const post = {
    id: postId,
    platform: 'instagram',
    format: 'feed',
    formatPreset: 'portrait',
    width: canvas.width || 1080,
    height: canvas.height || 1350,
    status: 'draft',
    name: 'Editable Finished Ad',
    headline: (layers.find((l) => l.id === 'headline') || {}).content || '',
    description: '',
    caption: '',
    coverAssetId: masterBg,
    linked_project_id: TEMPLE,
    elements: layers,
    generationMeta: {
      provider: 'gpt_image',
      model: 'gpt-image-2',
      generated_by: 'creative_director_generate_ad',
      project_id: TEMPLE,
      campaign_context_id: gen.campaign_id,
      production_mode: 'editable_finished_ad',
      logo_asset_id: gen.logo_asset_id,
      interior_asset_id: gen.interior_asset_id,
      master_background_asset_id: masterBg,
      finished_ad_raster_asset_id: gen.finished_ad_raster_asset_id || gen.final_asset_id,
      design_spec: reviseD.design_spec || gen.design_spec,
      gpt_image: {
        local_asset_id: gen.final_asset_id,
        composition_base_asset_id: masterBg,
        editable_layers: true,
      },
    },
    campaignContextId: gen.campaign_id,
    generationLifecycle: 'ready',
  };

  const draftBody = {
    schemaVersion: 2,
    documentType: 'social',
    linkedProjectId: TEMPLE,
    coverImage: { asset_id: masterBg },
    galleryImages: [],
    posts: [post],
    selectedPostId: postId,
    brandLogo: false,
    designProvider: 'creative-director',
    savedAt: Date.now(),
  };

  await api(`/creative-studio/documents/${documentId}/draft`, {
    method: 'PUT',
    cookie,
    body: { draft_body_json: draftBody },
  });

  await page.addInitScript((projectId) => {
    try {
      localStorage.setItem('ih-smb-last-construction-project-id', projectId);
    } catch {
      /* ignore */
    }
  }, TEMPLE);

  await page.goto(`${BASE}/workspaces/creative-studio/social-media-builder`, {
    waitUntil: 'domcontentloaded',
    timeout: 90000,
  });
  await page.locator('[data-testid="smb-artboard"]').waitFor({ state: 'visible', timeout: 90000 });
  await page.waitForTimeout(4000);

  const editableCard = page
    .locator('[data-testid^="smb-post-card-"]')
    .filter({ hasText: /Editable Finished Ad/i })
    .locator('button.smb-ws__page-card-hit')
    .first();
  if (await editableCard.count()) {
    await editableCard.click();
    await page.waitForTimeout(2000);
  }

  const report = await page.evaluate(() => {
    const artboard = document.querySelector('[data-testid="smb-artboard"]');
    const dock = document.querySelector('[data-testid="smb-finished-ad-dock"]');
    const layers = [...document.querySelectorAll('[data-testid^="smb-el-"]')].map((el) => ({
      id: el.getAttribute('data-testid'),
      type: el.getAttribute('data-el-type'),
      role: el.getAttribute('data-el-role'),
    }));
    return {
      finishedAdCanvas: artboard?.getAttribute('data-finished-ad-canvas') === 'true',
      coverAssetId: artboard?.getAttribute('data-cover-asset-id') || null,
      dockVisible: Boolean(dock),
      layerCount: layers.length,
      layers,
    };
  });

  await page.screenshot({ path: path.join(OUT, 'smb-editable-finished-ad.png'), fullPage: false });
  const art = page.locator('[data-testid="smb-artboard"]');
  if (await art.count()) await art.screenshot({ path: path.join(OUT, 'smb-artboard.png') });

  const summary = {
    ...report,
    documentId,
    csProjectId,
    seededPostId: postId,
    production_mode: 'editable_finished_ad',
    screenshot: 'artifacts/editable-finished-ad/smb-editable-finished-ad.png',
    visual_quality: 'NOT_CLAIMED',
  };
  fs.writeFileSync(path.join(OUT, 'smb-screenshot-report.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
  await browser.close();
  process.exit(report.layerCount > 0 ? 0 : 2);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
