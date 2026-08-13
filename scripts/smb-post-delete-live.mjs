/**
 * Live Gönderiler post-delete acceptance on The Temple.
 * Does not print secrets. Run: node scripts/smb-post-delete-live.mjs
 */
import { createRequire } from 'node:module';
import { dirname as pathDirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = pathDirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(__dirname, '..', '.pw-verify', 'node_modules', 'playwright'));

const BASE = process.env.SMB_BASE_URL || 'http://localhost:3000';
const EMAIL = process.env.SMB_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.SMB_PASSWORD || 'Investhome2026!';
const SMB_PATH = '/workspaces/creative-studio/social-media-builder';
const TEMPLE_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const API = process.env.SMB_API_URL || 'http://localhost:8000';

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
  await page.waitForSelector('[data-testid="smb-post-strip"]', { timeout: 30000 });
}

async function postIds(page) {
  return page.evaluate(() =>
    [...document.querySelectorAll('[data-testid="smb-post-row"] [data-testid^="smb-post-card-"]')]
      .map((el) => (el.getAttribute('data-testid') || '').replace('smb-post-card-', ''))
      .filter(Boolean),
  );
}

async function selectedPostId(page) {
  return page.evaluate(() => {
    const el = document.querySelector('[data-testid^="smb-post-card-"].is-selected');
    return (el?.getAttribute('data-testid') || '').replace('smb-post-card-', '') || null;
  });
}

async function artboardState(page) {
  return page.evaluate(() => {
    const art = document.querySelector('[data-testid="smb-artboard"]');
    const img = document.querySelector('[data-testid="smb-artboard-img"]');
    return {
      state: art?.getAttribute('data-image-state') || '',
      cover: art?.getAttribute('data-cover-asset-id') || '',
      selected: art?.getAttribute('data-selected-post-id') || '',
      imgOk: Boolean(img && img.complete && img.naturalWidth > 0),
    };
  });
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
  await page.waitForFunction(
    () => /Gönderi silindi|Post deleted/i.test(document.body?.innerText || ''),
    null,
    { timeout: 20000 },
  );
  await page.waitForTimeout(600);
  const left = await postIds(page);
  if (left.includes(id)) throw new Error(`post ${id} still in strip after delete`);
}

async function ensureCount(page, n) {
  while ((await postIds(page)).length < n) {
    await page.click('[data-testid="smb-new-post"]');
    await page.waitForTimeout(500);
  }
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
  page.on('pageerror', (err) => console.log('PAGEERROR', err.message));

  let snapshot = null;
  let documentId = null;
  page.on('response', async (res) => {
    try {
      if (!res.ok()) return;
      const url = res.url();
      if (!url.includes('/creative-studio/documents')) return;
      const body = await res.json();
      if (body?.document_type && body.document_type !== 'social') return;
      if (body?.id) documentId = body.id;
      if (body?.draft_body_json && snapshot == null) snapshot = body.draft_body_json;
    } catch {
      /* ignore */
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

    const projectSelect = page.locator('#smb-project');
    if (await projectSelect.count()) {
      const values = await projectSelect.locator('option').evaluateAll((opts) =>
        opts.map((o) => o.value),
      );
      if (values.includes(TEMPLE_ID)) {
        const current = await projectSelect.inputValue();
        if (current !== TEMPLE_ID) {
          await projectSelect.selectOption(TEMPLE_ID);
          await page.waitForTimeout(1800);
          await waitReady(page);
        }
      }
    }

    await ensureCount(page, 3);
    let ids = await postIds(page);
    const idC = ids[2];
    await deletePost(page, idC);
    ids = await postIds(page);
    if (!ids.includes(idC)) pass('live-delete-C', `removed ${idC}; remain ${ids.length}`);
    else fail('live-delete-C', 'C still in strip');

    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitReady(page);
    ids = await postIds(page);
    if (!ids.includes(idC)) pass('live-reload', `C stayed deleted; remain ${ids.length}`);
    else fail('live-reload', 'C returned after refresh');

    await ensureCount(page, 3);
    ids = await postIds(page);
    const idB = ids[1];
    const expectedNearest = ids[2] || ids[0];
    await page.click(`[data-testid="smb-post-card-${idB}"] .smb-ws__page-card-hit`);
    await page.waitForTimeout(300);
    await deletePost(page, idB);
    const nearest = await selectedPostId(page);
    ids = await postIds(page);
    if (!ids.includes(idB) && nearest === expectedNearest) {
      pass('live-nearest-select', `deleted B ${idB} → ${nearest}`);
    } else {
      fail('live-nearest-select', `expected ${expectedNearest} got ${nearest}`);
    }

    ids = await postIds(page);
    const sharedHost = ids[0];
    await page.click(`[data-testid="smb-post-card-${sharedHost}"] .smb-ws__page-card-hit`);
    await page.waitForTimeout(500);
    const coverBefore = await artboardState(page);
    await page.click('[data-testid="smb-new-post"]');
    await page.waitForTimeout(700);
    const extra = (await postIds(page)).at(-1);
    await page.click(`[data-testid="smb-post-card-${sharedHost}"] .smb-ws__page-card-hit`);
    await page.waitForTimeout(300);
    await deletePost(page, extra);
    await page.click(`[data-testid="smb-post-card-${sharedHost}"] .smb-ws__page-card-hit`);
    await page.waitForTimeout(600);
    const coverAfter = await artboardState(page);
    const hostStillThere = (await postIds(page)).includes(sharedHost);
    if (!hostStillThere) {
      fail('live-shared-asset', `host ${sharedHost} missing after deleting extra`);
    } else if (coverBefore.cover && coverAfter.cover === coverBefore.cover) {
      pass('live-shared-asset', `asset ${coverAfter.cover.slice(0, 8)} still on host`);
    } else if (!coverBefore.cover) {
      pass('live-shared-asset', 'host had no cover — sibling post remained after extra delete');
    } else {
      fail(
        'live-shared-asset',
        `before=${coverBefore.cover}/${coverBefore.state} after=${coverAfter.cover}/${coverAfter.state}`,
      );
    }

    const beforeLast = await postIds(page);
    while ((await postIds(page)).length) {
      const left = await postIds(page);
      await deletePost(page, left[left.length - 1]);
    }
    const emptied = await postIds(page);
    const emptyArt = await artboardState(page);
    const newBtn = await page.locator('[data-testid="smb-new-post"]').count();
    if (emptied.length === 0 && newBtn && emptyArt.selected === '') {
      pass('live-last-post-empty', `artboard=${emptyArt.state}`);
    } else {
      fail('live-last-post-empty', `posts=${emptied.length} selected=${emptyArt.selected}`);
    }

    await page.click('[data-testid="smb-new-post"]');
    await page.waitForTimeout(700);
    const created = await postIds(page);
    if (created.length === 1) pass('live-create-after-delete', `new ${created[0]}`);
    else fail('live-create-after-delete', `count=${created.length}`);

    if (documentId && snapshot) {
      const restored = await page.evaluate(
        async ({ api, docId, body }) => {
          const res = await fetch(`${api}/creative-studio/documents/${docId}/draft`, {
            method: 'PUT',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ draft_body_json: body }),
          });
          return res.ok;
        },
        { api: API, docId: documentId, body: snapshot },
      );
      if (restored) pass('live-restore-draft', 'original Temple posts restored');
      else fail('live-restore-draft', 'PUT draft failed');
    } else {
      fail('live-restore-draft', 'no snapshot captured');
    }
  } catch (err) {
    fail('live-runner', err instanceof Error ? err.message : String(err));
  } finally {
    await browser.close();
    const failed = results.filter((r) => !r.ok);
    console.log(`SUMMARY ${results.filter((r) => r.ok).length}/${results.length} passed`);
    if (failed.length) process.exitCode = 1;
  }
}

await main();
