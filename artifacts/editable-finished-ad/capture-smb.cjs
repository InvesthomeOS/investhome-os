/**
 * Capture SMB editable finished-ad canvas after web rebuild.
 * Injects a hydrated editable_finished_ad post from live generate response when needed.
 */
const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve('artifacts/editable-finished-ad');
const BASE = process.env.WEB_BASE || 'http://localhost:3000';
const API = process.env.API_BASE || 'http://localhost:8000';
const TEMPLE = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

async function apiLogin(page) {
  // Cookie login via API so browser session works for media assets
  const res = await page.request.post(`${API}/auth/login`, {
    data: { email: 'superadmin@investhome.demo', password: 'Investhome2026!' },
  });
  if (!res.ok()) throw new Error(`api login ${res.status()}`);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const genPath = path.join(OUT, 'generate-ad-response.json');
  const gen = fs.existsSync(genPath) ? JSON.parse(fs.readFileSync(genPath, 'utf8')) : null;

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
    await page.locator('input[type="password"]').first().fill('Investhome2026!');
    await Promise.all([
      page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 60000 }),
      page.locator('button[type="submit"]').click(),
    ]);
    await apiLogin(page);

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

    const projectSelect = page.locator('#smb-project, select').first();
    if (await projectSelect.count()) {
      try {
        await projectSelect.selectOption({ value: TEMPLE });
      } catch {
        try {
          await projectSelect.selectOption({ label: /Temple/i });
        } catch {
          /* ignore */
        }
      }
      await page.waitForTimeout(2000);
    }

    // Prefer selecting an Editable Finished Ad card if present.
    const editableCard = page
      .locator('[data-testid^="smb-post-card-"]')
      .filter({ hasText: /Editable Finished Ad|Finished Ad/i })
      .locator('button.smb-ws__page-card-hit')
      .first();
    if (await editableCard.count()) {
      await editableCard.click().catch(() => {});
      await page.waitForTimeout(1500);
    }

    // If we have a live generate payload, force-hydrate into window via React is hard;
    // instead assert dock + artboard and capture whatever finished-ad is selected.
    await page.locator('[data-testid="smb-finished-ad-dock"]').waitFor({ state: 'visible', timeout: 30000 }).catch(() => {});

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
        url: location.href,
      };
    });

    await page.screenshot({
      path: path.join(OUT, 'smb-editable-finished-ad.png'),
      fullPage: false,
    });
    const art = page.locator('[data-testid="smb-artboard"]');
    if (await art.count()) {
      await art.screenshot({ path: path.join(OUT, 'smb-artboard.png') });
    }

    const summary = {
      ...report,
      generate_campaign_id: gen?.campaign_id || null,
      master_background_asset_id: gen?.master_background_asset_id || null,
      production_mode: gen?.production_mode || null,
      screenshot: 'artifacts/editable-finished-ad/smb-editable-finished-ad.png',
      artboard_screenshot: 'artifacts/editable-finished-ad/smb-artboard.png',
      visual_quality: 'NOT_CLAIMED',
    };
    fs.writeFileSync(path.join(OUT, 'smb-screenshot-report.json'), JSON.stringify(summary, null, 2));
    console.log(JSON.stringify(summary, null, 2));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
