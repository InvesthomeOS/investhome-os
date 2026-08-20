/**
 * Real SMB screenshot after finished-ad revision hydrate (0 GPT calls).
 * Draft was seeded with createFinishedAdCanvasPost-shaped revised final asset.
 */
const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve('artifacts/ai-revision-display-fix');
const BASE = process.env.WEB_BASE || 'http://127.0.0.1:3000';
const LINKED = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const REVISED = JSON.parse(fs.readFileSync(path.join(OUT, 'summary.json'), 'utf8')).revised_asset_id;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.getByLabel(/email|e-posta/i).fill('superadmin@investhome.demo').catch(async () => {
      await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
    });
    await page.locator('input[type="password"], input[name="password"]').first().fill('Investhome2026!');
    await page.getByRole('button', { name: /giriş|sign in|log in/i }).click();
    await page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 60000 });

    // Prefer Temple construction project for SMB restore.
    await page.addInitScript((projectId) => {
      try {
        localStorage.setItem('cs.smb.lastConstructionProjectId', projectId);
        localStorage.setItem('cs.builder.lastConstructionProjectId', projectId);
        localStorage.setItem('creative-studio.lastConstructionProjectId', projectId);
      } catch {}
    }, LINKED);

    await page.goto(`${BASE}/workspaces/creative-studio/social-media-builder`, {
      waitUntil: 'domcontentloaded',
      timeout: 90000,
    });

    // Select Temple if a project picker is visible.
    const projectSelect = page.locator('select, [data-testid*="project"]').first();
    if (await projectSelect.count()) {
      try {
        await projectSelect.selectOption({ label: /Temple/i });
      } catch {
        /* ignore */
      }
    }

    // Wait for finished-ad canvas hydration.
    const artboard = page.locator('[data-testid="smb-artboard"]');
    await artboard.waitFor({ state: 'visible', timeout: 90000 });

    // Poll until finished-ad flags match revised asset (draft hydrate).
    let meta = null;
    for (let i = 0; i < 40; i += 1) {
      meta = await page.evaluate(() => {
        const el = document.querySelector('[data-testid="smb-artboard"]');
        if (!el) return null;
        return {
          finished: el.getAttribute('data-finished-ad-canvas'),
          cover: el.getAttribute('data-cover-asset-id'),
          selected: el.getAttribute('data-selected-post-id'),
          textHits: Array.from(document.querySelectorAll('[data-testid="smb-artboard-design"] *'))
            .map((n) => (n.textContent || '').trim())
            .filter((t) => t === 'New social post' || t.includes('Özel tur planlayın')).length,
          img: Boolean(document.querySelector('[data-testid="smb-artboard-img"]')),
        };
      });
      if (meta?.finished === 'true' && meta.cover === REVISED && meta.img) break;
      // Try clicking a Finished Ad post in the rail if present
      const finishedRail = page.locator('text=Finished Ad').first();
      if (await finishedRail.count()) {
        await finishedRail.click().catch(() => {});
      }
      await page.waitForTimeout(1500);
    }

    await page.screenshot({
      path: path.join(OUT, 'smb-after-hydration.png'),
      fullPage: false,
    });
    fs.writeFileSync(path.join(OUT, 'smb-dom-meta.json'), JSON.stringify(meta, null, 2));
    console.log(JSON.stringify({ screenshot: 'smb-after-hydration.png', meta }, null, 2));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
