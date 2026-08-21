/**
 * Capture real SMB right edit panel after web rebuild.
 */
const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve('artifacts/smb-right-edit-panel');
const BASE = process.env.WEB_BASE || 'http://localhost:3000';
const TEMPLE_CONSTRUCTION_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 960 } });
  const report = {
    floatingToolbar: null,
    topFormatTabs: null,
    editPanelOpen: null,
    editContext: null,
    bottomActions: [],
    bottomActionCount: 0,
  };

  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
    await page.locator('input[type="password"]').first().fill('Investhome2026!');
    await Promise.all([
      page.waitForURL((u) => !u.pathname.includes('/login'), { timeout: 60000 }),
      page.locator('button[type="submit"]').click(),
    ]);

    await page.addInitScript((projectId) => {
      try {
        localStorage.setItem('ih-smb-last-construction-project-id', projectId);
      } catch {
        /* ignore */
      }
    }, TEMPLE_CONSTRUCTION_ID);

    await page.goto(`${BASE}/workspaces/creative-studio/social-media-builder`, {
      waitUntil: 'domcontentloaded',
      timeout: 90000,
    });

    await page.locator('[data-testid="smb-artboard"]').waitFor({ state: 'visible', timeout: 90000 });

    const projectSelect = page.locator('#smb-project, select').first();
    if (await projectSelect.count()) {
      try {
        await projectSelect.selectOption({ value: TEMPLE_CONSTRUCTION_ID });
      } catch {
        try {
          await projectSelect.selectOption({ label: /Temple/i });
        } catch {
          /* ignore */
        }
      }
      await page.waitForTimeout(2500);
    }

    for (let i = 0; i < 24; i += 1) {
      const finished = await page.evaluate(
        () =>
          document.querySelector('[data-testid="smb-artboard"]')?.getAttribute('data-finished-ad-canvas') ===
          'true',
      );
      if (finished) break;
      const finishedCard = page
        .locator('[data-testid^="smb-post-card-"]')
        .filter({ hasText: /Finished Ad/i })
        .locator('button.smb-ws__page-card-hit')
        .first();
      if (await finishedCard.count()) {
        await finishedCard.click().catch(() => {});
      } else {
        const cards = page.locator('[data-testid^="smb-post-card-"] button.smb-ws__page-card-hit');
        const n = await cards.count();
        if (n > 0) await cards.nth(Math.min(i, n - 1)).click().catch(() => {});
      }
      await page.waitForTimeout(600);
    }

    // Ensure edit panel open
    const closedTab = page.locator('[data-testid="smb-edit-panel-open"]');
    if (await closedTab.count()) {
      await closedTab.click();
      await page.waitForTimeout(400);
    }

    // Select a text layer if present to show contextual panel; otherwise keep design context
    const textEl = page.locator('[data-testid^="smb-el-"][data-el-type="TEXT"]').first();
    if (await textEl.count()) {
      await textEl.click({ force: true }).catch(() => {});
      await page.waitForTimeout(500);
    }

    report.floatingToolbar = await page.locator('[data-testid="smb-floating-actions"]').count();
    report.topFormatTabs = await page.locator('.smb-ws__format-tabs, [data-testid^="smb-format-"]').count();
    report.editPanelOpen = await page.locator('[data-testid="smb-edit-panel"]').count();
    report.editContext = await page
      .locator('[data-testid="smb-edit-panel"]')
      .first()
      .getAttribute('data-edit-context');

    const actions = page.locator('[data-testid="smb-bat"] [data-testid]');
    const n = await actions.count();
    for (let i = 0; i < n; i += 1) {
      const el = actions.nth(i);
      const testId = await el.getAttribute('data-testid');
      if (!testId || testId === 'smb-bat') continue;
      if (!/smb-(output|action)-/.test(testId)) continue;
      const label = ((await el.innerText().catch(() => '')) || '').replace(/\s+/g, ' ').trim();
      report.bottomActions.push({ testId, label });
    }
    report.bottomActionCount = report.bottomActions.length;

    await page.screenshot({
      path: path.join(OUT, 'smb-right-edit-panel.png'),
      fullPage: false,
    });
    await page.locator('[data-testid="smb-center"]').screenshot({
      path: path.join(OUT, 'smb-canvas-and-panel.png'),
    }).catch(() => {});

    fs.writeFileSync(path.join(OUT, 'verify-report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));
    console.log('SCREENSHOT', path.join(OUT, 'smb-right-edit-panel.png'));
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
