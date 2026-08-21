/**
 * Capture real SMB bottom teal bar after web rebuild.
 * Forces The Temple finished-ad draft, then verifies the 7-action dock.
 */
const { chromium } = require('C:/Users/eminb/Projects/investhome-os/.pw-verify/node_modules/playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.resolve('artifacts/smb-bottom-bar');
const BASE = process.env.WEB_BASE || 'http://localhost:3000';
const TEMPLE_CONSTRUCTION_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
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

    // Select Temple construction project if dropdown present.
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

    for (let i = 0; i < 30; i += 1) {
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
        if (n > 0) {
          await cards
            .nth(Math.min(i, n - 1))
            .click()
            .catch(() => {});
        }
      }
      await page.waitForTimeout(700);
    }

    await page.locator('[data-testid="smb-scene-actions"], [data-testid="smb-bat"]').first().waitFor({
      state: 'visible',
      timeout: 30000,
    });

    const report = await page.evaluate(() => {
      const pilot = document.querySelector('[data-testid="smb-pilot-output"]');
      const outputActions = document.querySelector('.smb-ws__output-actions');
      const bat = document.querySelector('[data-testid="smb-bat"]');
      const finishedDock = document.querySelector('[data-testid="smb-finished-ad-dock"]');
      const actions = bat
        ? Array.from(bat.querySelectorAll('button.cs-bat__action, button.cs-bat__primary-btn')).map((b) => ({
            testId: b.getAttribute('data-testid'),
            label:
              (b.querySelector('.cs-bat__action-label') || b.querySelector('span') || b).textContent?.trim() ||
              '',
            className: b.className,
            isPrimaryPill: b.classList.contains('cs-bat__primary-btn'),
          }))
        : [];
      const undo = document.querySelector('[data-testid="smb-action-undo"]');
      const artboardEl = document.querySelector('[data-testid="smb-artboard"]');
      const center = document.querySelector('[data-testid="smb-center"]');
      const aboveCanvasStory = Array.from(center?.querySelectorAll('button') || []).filter((b) => {
        const inDock = Boolean(b.closest('[data-testid="smb-scene-actions"]'));
        const label = (b.textContent || '').trim();
        return !inDock && /Story Yap|Reel Yap|Varyasyon Oluştur/.test(label);
      });
      return {
        duplicatePilotOutput: Boolean(pilot || outputActions),
        aboveCanvasDuplicateCount: aboveCanvasStory.length,
        finishedAd: artboardEl?.getAttribute('data-finished-ad-canvas') === 'true',
        finishedDock: Boolean(finishedDock),
        actionCount: actions.filter((a) => a.testId !== 'smb-bat-more').length,
        actions,
        divider: Boolean(document.querySelector('[data-testid="smb-bat-divider"]')),
        undoIsPrimaryPill: undo?.classList.contains('cs-bat__primary-btn') === true,
        undoClass: undo?.className || null,
        storyInBat: Boolean(document.querySelector('[data-testid="smb-output-story"]')),
        reelInBat: Boolean(document.querySelector('[data-testid="smb-output-reel"]')),
        variationInBat: Boolean(document.querySelector('[data-testid="smb-output-variation"]')),
        downloadInBat: Boolean(document.querySelector('[data-testid="smb-action-download"]')),
        publishInBat: Boolean(document.querySelector('[data-testid="smb-action-publish"]')),
        redoInBat: Boolean(document.querySelector('[data-testid="smb-action-redo"]')),
      };
    });

    const dock = page.locator('[data-testid="smb-scene-actions"]');
    if (await dock.count()) {
      await dock.screenshot({ path: path.join(OUT, 'real-bottom-bar.png') });
    } else {
      await page.screenshot({ path: path.join(OUT, 'real-bottom-bar.png'), fullPage: false });
    }
    await page.screenshot({ path: path.join(OUT, 'real-smb-full.png'), fullPage: false });
    fs.writeFileSync(path.join(OUT, 'verify-report.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report, null, 2));

    const ok =
      !report.duplicatePilotOutput &&
      report.aboveCanvasDuplicateCount === 0 &&
      report.finishedAd &&
      report.finishedDock &&
      report.actionCount === 7 &&
      !report.undoIsPrimaryPill &&
      report.storyInBat &&
      report.reelInBat &&
      report.variationInBat &&
      report.downloadInBat &&
      report.publishInBat &&
      report.redoInBat &&
      report.divider;
    console.log(ok ? 'VERIFY_OK' : 'VERIFY_FAILED');
    process.exit(ok ? 0 : 2);
  } finally {
    await browser.close();
  }
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
