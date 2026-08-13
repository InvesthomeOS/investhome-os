/**
 * Live SMB multi-post asset rehydration (switch / reload / fullscreen / replace).
 * Does not print secrets. Run: node scripts/smb-asset-rehydration-live.mjs
 */
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(__dirname, '..', '.pw-verify', 'node_modules', 'playwright'));

const BASE = process.env.SMB_BASE_URL || 'http://localhost:3000';
const EMAIL = process.env.SMB_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.SMB_PASSWORD || 'Investhome2026!';
const SMB_PATH = '/workspaces/creative-studio/social-media-builder';
const TEMPLE_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';

const results = [];
function pass(name, detail = '') {
  results.push({ name, ok: true, detail });
  console.log(`PASS ${name}${detail ? ` — ${detail}` : ''}`);
}
function fail(name, detail = '') {
  results.push({ name, ok: false, detail });
  console.log(`FAIL ${name}${detail ? ` — ${detail}` : ''}`);
}

async function waitReady(page) {
  await page.waitForSelector('[data-testid="smb-workspace"]', { timeout: 90000 });
  await page.waitForSelector('[data-testid="smb-artboard"]', { timeout: 90000 });
  for (let i = 0; i < 40; i++) {
    const ready = await page.evaluate(() => Boolean(document.querySelector('[data-testid="smb-workspace"]')));
    if (ready) return;
    await page.waitForTimeout(500);
  }
}

async function postCards(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('[data-testid^="smb-post-card-"]')]
      .filter((n) => n.getAttribute('data-testid') !== 'smb-post-card-new')
      .map((n) => ({
        id: (n.getAttribute('data-testid') || '').replace('smb-post-card-', ''),
        selected: n.classList.contains('is-selected'),
        label: (n.querySelector('strong')?.textContent || '').trim(),
        hasThumb: Boolean(n.querySelector('img')),
      })),
  );
}

async function artboardSnapshot(page) {
  return page.evaluate(() => {
    const board = document.querySelector('[data-testid="smb-artboard"]');
    const img = document.querySelector('[data-testid="smb-artboard-img"]');
    const loading = document.querySelector('[data-testid="smb-artboard-loading"]');
    return {
      state: board?.getAttribute('data-image-state') || '',
      coverId: board?.getAttribute('data-cover-asset-id') || '',
      postId: board?.getAttribute('data-selected-post-id') || '',
      hasImg: Boolean(img),
      imgSrc: img?.getAttribute('src') || '',
      imgCoverId: img?.getAttribute('data-cover-asset-id') || '',
      loading: Boolean(loading),
      loadingText: loading?.textContent || '',
    };
  });
}

async function waitArtboardReady(page, timeoutMs = 60000) {
  const start = Date.now();
  let last = null;
  while (Date.now() - start < timeoutMs) {
    last = await artboardSnapshot(page);
    if (last.state === 'ready' && last.hasImg && last.coverId && last.imgSrc) return last;
    if (last.state === 'error') return last;
    await page.waitForTimeout(400);
  }
  return last;
}

async function waitAiIdle(page, timeoutMs = 180000) {
  const start = Date.now();
  await page.waitForTimeout(1500);
  while (Date.now() - start < timeoutMs) {
    const disabled = await page.locator('[data-testid="smb-ai-design-submit"][disabled]').count();
    if (!disabled) return;
    await page.waitForTimeout(1000);
  }
  throw new Error('AI timeout');
}

async function createPost(page, prompt) {
  await page.fill('[data-testid="smb-ai-design-input"]', prompt);
  await page.click('[data-testid="smb-ai-design-submit"]');
  await waitAiIdle(page);
  await page.waitForTimeout(800);
}

async function editPost(page, prompt) {
  await page.fill('[data-testid="smb-ai-design-input"]', prompt);
  await page.click('[data-testid="smb-ai-design-edit"]');
  await waitAiIdle(page);
  await page.waitForTimeout(800);
}

async function selectTemple(page) {
  const projectSelect = page.locator('#smb-project');
  if (!(await projectSelect.count())) return false;
  const values = await projectSelect.locator('option').evaluateAll((opts) => opts.map((o) => o.value));
  if (values.includes(TEMPLE_ID)) {
    await projectSelect.selectOption(TEMPLE_ID);
    await page.waitForTimeout(2500);
    await waitReady(page);
    return true;
  }
  const options = await projectSelect.locator('option').allTextContents();
  const temple = options.findIndex((o) => /temple/i.test(o));
  if (temple >= 0) {
    const value = await projectSelect.locator('option').nth(temple).getAttribute('value');
    if (value) {
      await projectSelect.selectOption(value);
      await page.waitForTimeout(2500);
      await waitReady(page);
      return true;
    }
  }
  return false;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('pageerror', (err) => console.log('PAGEERROR', err.message));

  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.fill('input[type="email"], input[name="email"]', EMAIL);
    await page.fill('input[type="password"], input[name="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(1500);
    await page.goto(`${BASE}${SMB_PATH}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await waitReady(page);
    await selectTemple(page);

    // ---- CREATE A (location) ----
    let snapA = null;
    let postAId = null;
    try {
      await createPost(
        page,
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium bir Instagram kare postu hazırla. Proje verilerini kullan. En uygun gerçek proje görselini seç. İngilizce hazırla.",
      );
      snapA = await waitArtboardReady(page);
      const cards = await postCards(page);
      postAId = cards.find((c) => c.selected)?.id || cards[cards.length - 1]?.id;
      if (snapA?.state === 'ready' && snapA.coverId && snapA.hasImg && postAId) {
        pass('CREATE_A', `post=${postAId} asset=${snapA.coverId}`);
      } else {
        fail('CREATE_A', JSON.stringify(snapA));
      }
    } catch (e) {
      fail('CREATE_A', String(e.message || e));
    }

    // ---- CREATE B (architecture) ----
    let snapB = null;
    let postBId = null;
    try {
      await createPost(
        page,
        'The Temple mimarisini ve dış cephe detaylarını öne çıkaran premium bir Instagram kare postu hazırla. En uygun gerçek The Temple exterior görselini seç. İngilizce hazırla.',
      );
      snapB = await waitArtboardReady(page);
      const cards = await postCards(page);
      postBId = cards.find((c) => c.selected)?.id || cards[cards.length - 1]?.id;
      const aStill = cards.some((c) => c.id === postAId);
      if (
        snapB?.state === 'ready' &&
        snapB.coverId &&
        snapB.hasImg &&
        postBId &&
        postBId !== postAId &&
        aStill
      ) {
        pass('CREATE_B', `post=${postBId} asset=${snapB.coverId}`);
      } else {
        fail('CREATE_B', JSON.stringify({ snapB, postBId, postAId, aStill }));
      }
    } catch (e) {
      fail('CREATE_B', String(e.message || e));
    }

    // ---- Switch A/B/A/B ----
    try {
      const seen = [];
      for (const id of [postAId, postBId, postAId, postBId]) {
        if (!id) throw new Error('missing post id');
        await page.click(`[data-testid="smb-post-card-${id}"]`);
        const snap = await waitArtboardReady(page, 20000);
        seen.push({
          id,
          coverId: snap?.coverId,
          state: snap?.state,
          hasImg: snap?.hasImg,
          loading: snap?.loading,
        });
      }
      const aOk = seen[0]?.coverId === snapA?.coverId && seen[2]?.coverId === snapA?.coverId && seen[0]?.hasImg && seen[2]?.hasImg;
      const bOk = seen[1]?.coverId === snapB?.coverId && seen[3]?.coverId === snapB?.coverId && seen[1]?.hasImg && seen[3]?.hasImg;
      const stuck = seen.some((s) => s.loading || s.state === 'loading');
      if (aOk && bOk && !stuck) {
        pass('SWITCH', `A=${snapA?.coverId} B=${snapB?.coverId}`);
      } else {
        fail('SWITCH', JSON.stringify(seen));
      }
    } catch (e) {
      fail('SWITCH', String(e.message || e));
    }

    // ---- Reload with B selected, then select A ----
    try {
      if (postBId) {
        await page.click(`[data-testid="smb-post-card-${postBId}"]`);
        await waitArtboardReady(page, 20000);
      }
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitReady(page);
      await selectTemple(page);
      const afterReloadB = await waitArtboardReady(page, 45000);
      const cards = await postCards(page);
      const selected = cards.find((c) => c.selected);
      if (postAId) {
        await page.click(`[data-testid="smb-post-card-${postAId}"]`);
      }
      const afterReloadA = await waitArtboardReady(page, 20000);
      const bReady = afterReloadB?.state === 'ready' && afterReloadB.hasImg && afterReloadB.coverId;
      const aReady = afterReloadA?.state === 'ready' && afterReloadA.hasImg && afterReloadA.coverId === snapA?.coverId;
      const bKept = !selected || selected.id === postBId || afterReloadB.coverId === snapB?.coverId;
      if (bReady && aReady && bKept) {
        pass('RELOAD', `B asset=${afterReloadB.coverId} A asset=${afterReloadA.coverId}`);
      } else {
        fail('RELOAD', JSON.stringify({ afterReloadB, afterReloadA, selected }));
      }
    } catch (e) {
      fail('RELOAD', String(e.message || e));
    }

    // ---- Fullscreen A and B ----
    try {
      async function fsCycle(postId, expectedCover) {
        await page.click(`[data-testid="smb-post-card-${postId}"]`);
        const before = await waitArtboardReady(page, 20000);
        const fsBtn = page.locator('[data-testid="smb-fullscreen-zoom"]').first();
        if (await fsBtn.count()) {
          await fsBtn.click({ force: true });
          await page.waitForTimeout(800);
        }
        const during = await artboardSnapshot(page);
        const fs = await page.evaluate(() => document.querySelector('[data-cs-fullscreen="true"]') != null);
        await page.keyboard.press('Escape');
        await page.waitForTimeout(500);
        const after = await waitArtboardReady(page, 20000);
        return {
          fs,
          before: before?.coverId,
          during: during?.coverId,
          duringImg: during?.hasImg,
          duringState: during?.state,
          after: after?.coverId,
          afterImg: after?.hasImg,
          expectedCover,
        };
      }
      const aFs = await fsCycle(postAId, snapA?.coverId);
      const bFs = await fsCycle(postBId, snapB?.coverId);
      const aOk =
        aFs.before === aFs.expectedCover &&
        aFs.during === aFs.expectedCover &&
        aFs.after === aFs.expectedCover &&
        aFs.duringImg &&
        aFs.afterImg &&
        aFs.duringState === 'ready';
      const bOk =
        bFs.before === bFs.expectedCover &&
        bFs.during === bFs.expectedCover &&
        bFs.after === bFs.expectedCover &&
        bFs.duringImg &&
        bFs.afterImg &&
        bFs.duringState === 'ready';
      if (aOk && bOk) {
        pass('FULLSCREEN', `A/B images survived enter/exit`);
      } else {
        fail('FULLSCREEN', JSON.stringify({ aFs, bFs }));
      }
    } catch (e) {
      fail('FULLSCREEN', String(e.message || e));
    }

    // ---- AI EDIT B replace image ----
    try {
      if (postBId) {
        await page.click(`[data-testid="smb-post-card-${postBId}"]`);
        await waitArtboardReady(page, 20000);
      }
      const before = await artboardSnapshot(page);
      await editPost(page, 'Başka bir gerçek The Temple exterior görseli kullan.');
      const after = await waitArtboardReady(page, 60000);
      if (postAId) {
        await page.click(`[data-testid="smb-post-card-${postAId}"]`);
      }
      const aAfter = await waitArtboardReady(page, 20000);
      const bHasImage = after?.state === 'ready' && after.hasImg && after.coverId;
      const aIntact = aAfter?.coverId === snapA?.coverId && aAfter?.hasImg;
      if (bHasImage && aIntact) {
        pass(
          'REPLACE',
          `B ${before.coverId}→${after.coverId}; A intact ${aAfter.coverId}`,
        );
      } else {
        fail('REPLACE', JSON.stringify({ before, after, aAfter }));
      }
    } catch (e) {
      fail('REPLACE', String(e.message || e));
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((r) => !r.ok);
  console.log(`SUMMARY ${results.filter((r) => r.ok).length}/${results.length} passed`);
  if (failed.length) process.exit(1);
}

main().catch((err) => {
  console.error(String(err?.message || err));
  process.exit(1);
});
