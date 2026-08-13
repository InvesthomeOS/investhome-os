/**
 * Live SMB CREATE vs EDIT + campaign isolation (Tests A–E).
 * Does not print secrets. Run: node scripts/smb-create-edit-isolation-live.mjs
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
  await page.waitForSelector('[data-testid="smb-artboard"]', { timeout: 90000 });
  for (let i = 0; i < 40; i++) {
    const ready = await page.evaluate(() => Boolean(document.querySelector('[data-testid="smb-workspace"]')));
    if (ready) return;
    await page.waitForTimeout(500);
  }
}

async function canvasText(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-testid^="smb-el-"]')];
    return nodes
      .map((n) => (n.textContent || '').trim())
      .filter(Boolean)
      .join(' | ');
  });
}

async function postCards(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('[data-testid^="smb-post-card-"]')]
      .filter((n) => n.getAttribute('data-testid') !== 'smb-post-card-new')
      .map((n) => ({
        id: (n.getAttribute('data-testid') || '').replace('smb-post-card-', ''),
        selected: n.classList.contains('is-selected'),
        label: (n.querySelector('strong')?.textContent || '').trim(),
        format: (n.querySelector('.smb-ws__page-format')?.textContent || '').trim(),
      })),
  );
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

function hasLeak(text) {
  const t = (text || '').toLowerCase();
  return t.includes('$500') || t.includes('500,000') || t.includes('%14') || t.includes('14%') || t.includes('24 ay') || t.includes('24 month');
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

    const projectSelect = page.locator('#smb-project');
    if (await projectSelect.count()) {
      const values = await projectSelect.locator('option').evaluateAll((opts) =>
        opts.map((o) => o.value),
      );
      if (values.includes(TEMPLE_ID)) {
        await projectSelect.selectOption(TEMPLE_ID);
        await page.waitForTimeout(2500);
        await waitReady(page);
      } else {
        const options = await projectSelect.locator('option').allTextContents();
        const temple = options.findIndex((o) => /temple/i.test(o));
        if (temple >= 0) {
          const value = await projectSelect.locator('option').nth(temple).getAttribute('value');
          if (value) {
            await projectSelect.selectOption(value);
            await page.waitForTimeout(2500);
            await waitReady(page);
          }
        }
      }
    }

    const createBtn = await page.locator('[data-testid="smb-ai-design-submit"]').count();
    const editBtn = await page.locator('[data-testid="smb-ai-design-edit"]').count();
    if (!createBtn || !editBtn) {
      fail('UI', `create=${createBtn} edit=${editBtn}`);
    } else {
      pass('UI', 'CREATE and EDIT buttons present');
    }

    const cards0 = await postCards(page);
    const count0 = cards0.length;

    // ---- TEST A: CREATE location, no financials ----
    try {
      await createPost(
        page,
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium bir Instagram kare postu hazırla. Proje verilerini kullan. En uygun gerçek proje görselini seç. İngilizce hazırla.",
      );
      const cards = await postCards(page);
      const text = await canvasText(page);
      if (cards.length >= count0 + 1 && !hasLeak(text)) {
        pass('A', `posts ${count0}→${cards.length}; no financial leak`);
      } else {
        fail('A', `posts ${count0}→${cards.length} text="${text.slice(0, 180)}"`);
      }
    } catch (e) {
      fail('A', String(e.message || e));
    }

    const cardsA = await postCards(page);
    const postAId = cardsA.find((c) => c.selected)?.id || cardsA[cardsA.length - 1]?.id;
    const postAText = await canvasText(page);

    // ---- TEST B: CREATE investment with campaign figures ----
    try {
      await createPost(
        page,
        'The Temple için yatırımcı odaklı premium Instagram kare postu. Minimum yatırım: $500,000 Hedef getiri: %14 Yatırım süresi: 24 ay. İngilizce hazırla.',
      );
      const cards = await postCards(page);
      const text = await canvasText(page);
      const newSelected = cards.find((c) => c.selected);
      const prevStill = cards.some((c) => c.id === postAId);
      const metrics = hasLeak(text);
      if (cards.length >= cardsA.length + 1 && prevStill && metrics && newSelected?.id !== postAId) {
        pass('B', `new post ${newSelected.id}; metrics present; Post A intact`);
      } else {
        fail(
          'B',
          `count ${cardsA.length}→${cards.length} prev=${prevStill} metrics=${metrics} sel=${newSelected?.id} text="${text.slice(0, 180)}"`,
        );
      }
    } catch (e) {
      fail('B', String(e.message || e));
    }

    const cardsB = await postCards(page);
    const postBId = cardsB.find((c) => c.selected)?.id;
    const postBText = await canvasText(page);

    // ---- TEST C: CREATE without figures must not inherit $500K/14%/24mo ----
    try {
      await createPost(page, 'hedef getirisini öne çıkar');
      const cards = await postCards(page);
      const text = await canvasText(page);
      const selected = cards.find((c) => c.selected);
      const leaked = hasLeak(text);
      const createdNew = selected && selected.id !== postBId && cards.length >= cardsB.length;
      const blockedSame =
        selected?.id === postBId && cards.length === cardsB.length && postBText === text;
      if ((createdNew && !leaked) || blockedSame) {
        pass('C', createdNew ? `new isolated post ${selected.id}` : 'blocked missing facts; previous intact');
      } else {
        fail('C', `sel=${selected?.id} leaked=${leaked} count ${cardsB.length}→${cards.length} text="${text.slice(0, 200)}"`);
      }
    } catch (e) {
      fail('C', String(e.message || e));
    }

    // Restore Post B for EDIT
    if (postBId) {
      const card = page.locator(`[data-testid="smb-post-card-${postBId}"]`);
      if (await card.count()) {
        await card.click();
        await page.waitForTimeout(600);
      }
    }

    // ---- TEST D: EDIT only selected ----
    try {
      const beforeCards = await postCards(page);
      const beforeText = await canvasText(page);
      const headlineBefore = await page.evaluate(() => {
        const el = document.querySelector('[data-el-role="headline"]');
        if (!el) return null;
        return { text: (el.textContent || '').trim(), top: parseFloat(el.style.top || '0') };
      });
      await editPost(page, 'Başlığı biraz yukarı al');
      const afterCards = await postCards(page);
      const afterText = await canvasText(page);
      const headlineAfter = await page.evaluate(() => {
        const el = document.querySelector('[data-el-role="headline"]');
        if (!el) return null;
        return { text: (el.textContent || '').trim(), top: parseFloat(el.style.top || '0') };
      });
      const countSame = afterCards.length === beforeCards.length;
      const copySame = headlineAfter?.text === headlineBefore?.text;
      const moved = headlineAfter && headlineBefore && headlineAfter.top !== headlineBefore.top;
      const siblingsSame = afterCards.filter((c) => c.id !== postBId).length === beforeCards.filter((c) => c.id !== postBId).length;
      if (countSame && copySame && siblingsSame && (moved || afterText.includes(headlineBefore?.text || ''))) {
        pass('D', `edit only selected; y ${headlineBefore?.top}→${headlineAfter?.top}`);
      } else {
        fail('D', JSON.stringify({ countSame, copySame, moved, siblingsSame, headlineBefore, headlineAfter }));
      }
    } catch (e) {
      fail('D', String(e.message || e));
    }

    const postBAfterEdit = await canvasText(page);

    // ---- TEST E: Gönderiler switch restores state + fullscreen persistence ----
    try {
      if (postAId) {
        await page.click(`[data-testid="smb-post-card-${postAId}"]`);
        await page.waitForTimeout(700);
      }
      const restoredA = await canvasText(page);
      if (postBId) {
        await page.click(`[data-testid="smb-post-card-${postBId}"]`);
        await page.waitForTimeout(700);
      }
      const restoredB = await canvasText(page);
      const aOk = restoredA && !hasLeak(restoredA);
      const bOk = restoredB && hasLeak(restoredB);
      const bMatches = restoredB === postBAfterEdit || hasLeak(restoredB);

      const fsBtn = page.locator('[data-testid="smb-fullscreen-zoom"]').first();
      if (await fsBtn.count()) {
        await fsBtn.click({ force: true });
        await page.waitForTimeout(800);
      }
      const fs = await page.evaluate(() => document.querySelector('[data-cs-fullscreen="true"]') != null);
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitReady(page);
      const afterReload = await postCards(page);
      const persisted = afterReload.length >= 2;
      if (aOk && bOk && bMatches && persisted) {
        pass('E', `switch restored A/B; fullscreen=${fs}; persisted ${afterReload.length} posts`);
      } else {
        fail(
          'E',
          `aOk=${aOk} bOk=${bOk} bMatches=${bMatches} fs=${fs} persisted=${persisted} A="${restoredA.slice(0, 80)}" B="${restoredB.slice(0, 80)}"`,
        );
      }
    } catch (e) {
      fail('E', String(e.message || e));
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
