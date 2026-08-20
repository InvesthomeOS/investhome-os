/**
 * Real SMB screenshot after finished-ad revision hydrate (0 GPT calls).
 */
const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve('artifacts/ai-revision-display-fix');
const BASE = process.env.WEB_BASE || 'http://localhost:3000';
const LINKED = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const REVISED = JSON.parse(fs.readFileSync(path.join(OUT, 'summary.json'), 'utf8')).revised_asset_id;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({
    headless: true,
    channel: process.env.PW_CHANNEL || 'msedge',
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  page.setDefaultTimeout(60000);
  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('input[type="email"]').fill('superadmin@investhome.demo');
    await page.locator('input[type="password"]').fill('Investhome2026!');
    await Promise.all([
      page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 90000 }),
      page.getByRole('button', { name: 'Giriş Yap' }).click(),
    ]);

    await page.evaluate((projectId) => {
      localStorage.setItem('ih-smb-last-construction-project-id', projectId);
    }, LINKED);

    await page.goto(`${BASE}/workspaces/creative-studio/social-media-builder`, {
      waitUntil: 'domcontentloaded',
      timeout: 90000,
    });

    const artboard = page.locator('[data-testid="smb-artboard"]');
    await artboard.waitFor({ state: 'visible', timeout: 120000 });

    // Prefer Temple in construction project picker if present.
    const templeOption = page.locator('option', { hasText: /Temple/i }).first();
    if (await templeOption.count()) {
      const select = page.locator('select').filter({ has: templeOption }).first();
      if (await select.count()) {
        await select.selectOption({ label: /Temple/i }).catch(() => {});
      }
    }

    let meta = null;
    for (let i = 0; i < 45; i += 1) {
      meta = await page.evaluate((revised) => {
        const el = document.querySelector('[data-testid="smb-artboard"]');
        if (!el) return null;
        const bodyText = document.body?.innerText || '';
        return {
          finished: el.getAttribute('data-finished-ad-canvas'),
          cover: el.getAttribute('data-cover-asset-id'),
          selected: el.getAttribute('data-selected-post-id'),
          hasNewSocialPost: bodyText.includes('New social post'),
          hasOzelTur: bodyText.includes('Özel tur planlayın'),
          img: Boolean(document.querySelector('[data-testid="smb-artboard-img"]')),
          revisedMatch: el.getAttribute('data-cover-asset-id') === revised,
        };
      }, REVISED);

      if (meta?.finished === 'true' && meta.revisedMatch && meta.img) break;

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
