/**
 * Live SMB + Yeni Post Oluştur generation after post-delete (Tests A/B/delete+create).
 * Does not print secrets. Run: node scripts/smb-new-post-generation-live.mjs
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
  await page.waitForSelector('[data-testid="smb-ai-design-submit"]', { timeout: 30000 });
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
      })),
  );
}

async function artboard(page) {
  return page.evaluate(() => {
    const art = document.querySelector('[data-testid="smb-artboard"]');
    const img = document.querySelector('[data-testid="smb-artboard-img"]');
    const lifecycle = art?.getAttribute('data-generation-lifecycle') || '';
    return {
      state: art?.getAttribute('data-image-state') || '',
      cover: art?.getAttribute('data-cover-asset-id') || '',
      selected: art?.getAttribute('data-selected-post-id') || '',
      lifecycle,
      imgOk: Boolean(img && img.complete && img.naturalWidth > 0),
      placeholder: /New social post/i.test(document.body?.innerText || ''),
    };
  });
}

async function waitAiIdle(page, timeoutMs = 180000) {
  const start = Date.now();
  await page.waitForSelector('[data-testid="smb-ai-design-submit"][disabled]', { timeout: 15000 });
  while (Date.now() - start < timeoutMs) {
    const disabled = await page.locator('[data-testid="smb-ai-design-submit"][disabled]').count();
    if (!disabled) return;
    await page.waitForTimeout(1000);
  }
  throw new Error('AI timeout');
}

async function toastText(page) {
  return page.evaluate(() => {
    const el = document.querySelector('.smb-ws__toast');
    return (el?.textContent || '').trim();
  });
}

async function createPost(page, prompt) {
  const input = page.locator('[data-testid="smb-ai-design-input"]');
  await input.waitFor({ state: 'visible', timeout: 15000 });
  await input.click({ force: true });
  await input.fill(prompt);
  const typed = await input.inputValue();
  if (!typed.trim()) throw new Error('prompt did not type into AI input');
  await page.click('[data-testid="smb-ai-design-submit"]', { force: true });
  await waitAiIdle(page);
  await page.waitForTimeout(1200);
  const toast = await toastText(page);
  if (toast) console.log('TOAST', toast);
}

async function deletePost(page, id) {
  const card = page.locator(`[data-testid="smb-post-card-${id}"]`);
  await card.scrollIntoViewIfNeeded();
  await card.hover();
  const more = page.locator(`[data-testid="smb-post-more-${id}"]`);
  await more.waitFor({ state: 'attached', timeout: 8000 });
  await more.click({ force: true });
  await page.click(`[data-testid="smb-post-delete-${id}"]`);
  await page.waitForSelector('[data-testid="smb-post-delete-confirm"]', { timeout: 8000 });
  await page.click('[data-testid="smb-post-delete-confirm"]');
  await page.waitForFunction(
    (postId) => !document.querySelector(`[data-testid="smb-post-card-${postId}"]`),
    id,
    { timeout: 15000 },
  );
}

function looksGenerated(text, board) {
  const t = (text || '').trim();
  if (!t || /New social post/i.test(t)) return false;
  if (board.placeholder) return false;
  if (board.lifecycle === 'generating' || board.lifecycle === 'error') return false;
  if (board.state === 'ready' && board.cover && board.imgOk) return true;
  if (board.cover && t.length > 8) return true;
  return false;
}

async function selectTemple(page) {
  const projectSelect = page.locator('#smb-project');
  if (!(await projectSelect.count())) return;
  const values = await projectSelect.locator('option').evaluateAll((opts) =>
    opts.map((o) => o.value),
  );
  if (values.includes(TEMPLE_ID)) {
    await projectSelect.selectOption(TEMPLE_ID);
    await page.waitForTimeout(2500);
    await waitReady(page);
    return;
  }
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

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('pageerror', (err) => console.log('PAGEERROR', err.message));
  page.on('response', (res) => {
    const url = res.url();
    if (url.includes('/social/design') || url.includes('/creative-studio')) {
      console.log('HTTP', res.status(), url.replace(/^https?:\/\/[^/]+/, ''));
    }
  });

  try {
    await page.goto(`${BASE}/login`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForSelector('input[type="email"]', { timeout: 30000 });
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForFunction(() => !window.location.pathname.includes('/login'), null, {
      timeout: 45000,
    });
    await page.goto(`${BASE}${SMB_PATH}`, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await waitReady(page);
    await selectTemple(page);

    const cards0 = await postCards(page);
    const count0 = cards0.length;

    // ---- TEST A: location prompt via + Yeni Post Oluştur ----
    let postAId = null;
    try {
      await createPost(
        page,
        "The Temple'ın Washington DC'deki merkezi lokasyon avantajını anlatan premium bir Instagram kare postu hazırla.",
      );
      const cards = await postCards(page);
      const text = await canvasText(page);
      const board = await artboard(page);
      const selected = cards.find((c) => c.selected);
      postAId = selected?.id || null;
      if (cards.length >= count0 + 1 && looksGenerated(text, board) && postAId) {
        pass('A', `id=${postAId} cover=${board.cover.slice(0, 8)} state=${board.state} text="${text.slice(0, 80)}"`);
      } else {
        fail(
          'A',
          `count ${count0}→${cards.length} state=${board.state} cover=${board.cover} lifecycle=${board.lifecycle} placeholder=${board.placeholder} text="${text.slice(0, 180)}"`,
        );
      }
    } catch (e) {
      fail('A', String(e.message || e));
    }

    // ---- TEST B: independent architecture post ----
    let postBId = null;
    try {
      await createPost(
        page,
        'The Temple mimarisini öne çıkaran bağımsız premium bir Instagram kare postu hazırla. Proje görsellerini kullan.',
      );
      const cards = await postCards(page);
      const text = await canvasText(page);
      const board = await artboard(page);
      const selected = cards.find((c) => c.selected);
      postBId = selected?.id || null;
      const aRemains = postAId ? cards.some((c) => c.id === postAId) : true;
      if (cards.length >= (postAId ? count0 + 2 : count0 + 1) && looksGenerated(text, board) && postBId && postBId !== postAId && aRemains) {
        pass('B', `id=${postBId} A intact=${aRemains} cover=${board.cover.slice(0, 8)}`);
      } else {
        fail(
          'B',
          `sel=${postBId} A=${postAId} remains=${aRemains} state=${board.state} text="${text.slice(0, 180)}"`,
        );
      }
    } catch (e) {
      fail('B', String(e.message || e));
    }

    // Switch A↔B
    try {
      if (postAId) {
        await page.click(`[data-testid="smb-post-card-${postAId}"]`);
        await page.waitForTimeout(800);
      }
      const aBoard = await artboard(page);
      const aText = await canvasText(page);
      if (postBId) {
        await page.click(`[data-testid="smb-post-card-${postBId}"]`);
        await page.waitForTimeout(800);
      }
      const bBoard = await artboard(page);
      const bText = await canvasText(page);
      if (looksGenerated(aText, aBoard) && looksGenerated(bText, bBoard) && aBoard.selected === postAId && bBoard.selected === postBId) {
        pass('switch', `A/B restored independently`);
      } else {
        fail('switch', `A sel=${aBoard.selected} B sel=${bBoard.selected} A="${aText.slice(0, 60)}" B="${bText.slice(0, 60)}"`);
      }
    } catch (e) {
      fail('switch', String(e.message || e));
    }

    // Delete A then create lifestyle C
    try {
      if (postAId) await deletePost(page, postAId);
      await page.waitForTimeout(800);
      const afterDelete = await postCards(page);
      const aGone = postAId ? !afterDelete.some((c) => c.id === postAId) : true;
      const bRemains = postBId ? afterDelete.some((c) => c.id === postBId) : true;
      await createPost(
        page,
        'The Temple lifestyle ve yaşama deneyimini anlatan premium bir Instagram kare postu hazırla.',
      );
      const cards = await postCards(page);
      const text = await canvasText(page);
      const board = await artboard(page);
      const cId = cards.find((c) => c.selected)?.id;
      if (aGone && bRemains && cId && cId !== postBId && looksGenerated(text, board)) {
        pass('delete+create', `A gone, B remains, C=${cId} state=${board.state}`);
      } else {
        fail(
          'delete+create',
          `aGone=${aGone} bRemains=${bRemains} c=${cId} state=${board.state} text="${text.slice(0, 160)}"`,
        );
      }
    } catch (e) {
      fail('delete+create', String(e.message || e));
    }

    // Reload persistence
    try {
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
      await waitReady(page);
      await selectTemple(page);
      const cards = await postCards(page);
      const text = await canvasText(page);
      const board = await artboard(page);
      const aGone = postAId ? !cards.some((c) => c.id === postAId) : true;
      const bRemains = postBId ? cards.some((c) => c.id === postBId) : cards.length > 0;
      if (aGone && bRemains && looksGenerated(text, board)) {
        pass('reload', `persisted ${cards.length} posts; A absent; generated canvas`);
      } else {
        fail(
          'reload',
          `aGone=${aGone} bRemains=${bRemains} count=${cards.length} state=${board.state} text="${text.slice(0, 160)}"`,
        );
      }
    } catch (e) {
      fail('reload', String(e.message || e));
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((r) => r.ok === false);
  console.log(`SUMMARY ${results.filter((r) => r.ok).length}/${results.length} passed`);
  if (failed.length) process.exit(1);
}

main().catch((err) => {
  console.error(String(err?.message || err));
  process.exit(1);
});
