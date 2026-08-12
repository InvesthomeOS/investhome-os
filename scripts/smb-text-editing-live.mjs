/**
 * Live Temple TEXT editing acceptance (Tests A–F) via Playwright.
 * Does not print secrets. Run: node scripts/smb-text-editing-live.mjs
 */
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(
  join(dirname(fileURLToPath(import.meta.url)), '../.pw-verify/package.json'),
);
const { chromium } = require('playwright');

const BASE = process.env.SMB_BASE_URL || 'http://localhost:3000';
const EMAIL = process.env.SMB_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.SMB_PASSWORD || 'Investhome2026!';
const SMB_PATH = '/workspaces/creative-studio/social-media-builder';

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
  await page.waitForSelector('[data-testid="smb-artboard"]', { timeout: 60000 });
  for (let i = 0; i < 40; i++) {
    const ready = await page.evaluate(() => {
      const art = document.querySelector('[data-testid="smb-artboard"]');
      const els = document.querySelectorAll('[data-el-type="TEXT"]');
      return Boolean(art && els.length >= 1);
    });
    if (ready) return;
    await page.waitForTimeout(500);
  }
}

async function headlineMeta(page) {
  return page.evaluate(() => {
    const nodes = [...document.querySelectorAll('[data-el-type="TEXT"]')].filter((n) => {
      const id = n.getAttribute('data-testid') || '';
      return id.startsWith('smb-el-') && !id.includes('editor') && !id.includes('resize');
    });
    const el =
      nodes.find((n) => n.getAttribute('data-el-role') === 'headline') || nodes[0];
    if (!el) return null;
    const id = (el.getAttribute('data-testid') || '').replace(/^smb-el-/, '');
    const editor = document.querySelector(`[data-testid="smb-el-editor-${id}"]`);
    const cs = getComputedStyle(el);
    const editorCs = editor ? getComputedStyle(editor) : null;
    return {
      id,
      text: editor ? editor.value : el.textContent || '',
      left: parseFloat(el.style.left || '0'),
      top: parseFloat(el.style.top || '0'),
      width: parseFloat(el.style.width || '0'),
      height: parseFloat(el.style.height || '0'),
      fontSize: parseFloat(cs.fontSize || '0'),
      lineHeight: cs.lineHeight,
      overflowY: cs.overflowY,
      editorOverflowY: editorCs?.overflowY || null,
      editorScroll: editor ? editor.scrollHeight - editor.clientHeight : 0,
      editing: el.classList.contains('is-editing'),
      exists: true,
    };
  });
}

async function openHeadlineEditor(page) {
  const meta = await headlineMeta(page);
  if (!meta) throw new Error('no headline');
  await page.evaluate((id) => {
    const el = document.querySelector(`[data-testid="smb-el-${id}"]`);
    el?.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, cancelable: true, view: window }));
  }, meta.id);
  const editor = page.locator(`[data-testid="smb-el-editor-${meta.id}"]`);
  await editor.waitFor({ state: 'attached', timeout: 5000 });
  await editor.click();
  return meta.id;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  page.on('pageerror', (err) => {
    console.log('PAGEERROR', err.message);
  });

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

    // ---- TEST A: Enter creates two lines ----
    let headlineId = '';
    try {
      headlineId = await openHeadlineEditor(page);
      const editor = page.locator(`[data-testid="smb-el-editor-${headlineId}"]`);
      await editor.press('Control+A');
      await editor.press('Backspace');
      await page.keyboard.type('Invest in');
      await page.keyboard.press('Enter');
      await page.keyboard.type('The Temple');
      await page.waitForTimeout(300);
      const after = await headlineMeta(page);
      const stillThere = Boolean(after?.exists && after.id === headlineId);
      const twoLines = (after?.text || '').includes('Invest in\nThe Temple');
      const noScroll =
        after &&
        after.overflowY !== 'auto' &&
        after.overflowY !== 'scroll' &&
        after.editorOverflowY !== 'auto' &&
        after.editorOverflowY !== 'scroll' &&
        after.editorScroll <= 2;
      const noClip = after && after.height >= 2;
      if (stillThere && twoLines && noScroll && noClip) {
        pass('A', `two lines h=${after.height} overflow=${after.overflowY}/${after.editorOverflowY}`);
      } else {
        fail(
          'A',
          `still=${stillThere} twoLines=${twoLines} noScroll=${noScroll} text=${JSON.stringify(after?.text)} h=${after?.height}`,
        );
      }
    } catch (e) {
      fail('A', String(e.message || e));
    }

    // ---- TEST B: third line grows the box ----
    try {
      const before = await headlineMeta(page);
      const editor = page.locator(`[data-testid="smb-el-editor-${headlineId}"]`);
      if (!(await editor.count())) {
        headlineId = await openHeadlineEditor(page);
      }
      await page.locator(`[data-testid="smb-el-editor-${headlineId}"]`).click();
      await page.keyboard.press('End');
      await page.keyboard.press('Enter');
      await page.keyboard.type('Line three');
      await page.waitForTimeout(350);
      const after = await headlineMeta(page);
      const grew = after && before && after.height > before.height;
      const three = (after?.text || '').split('\n').length >= 3;
      const inCanvas =
        after && after.left >= 0 && after.top >= 0 && after.left + after.width <= 1080 + 1;
      if (grew && three && inCanvas) pass('B', `h ${before.height}→${after.height}`);
      else fail('B', `grew=${grew} three=${three} inCanvas=${inCanvas} h=${after?.height}`);
    } catch (e) {
      fail('B', String(e.message || e));
    }

    // ---- TEST C: resize narrower wraps, no scrollbar ----
    try {
      await page.keyboard.press('Escape');
      await page.waitForTimeout(250);
      const before = await headlineMeta(page);
      headlineId = before?.id || headlineId;
      await page.evaluate((id) => {
        const el = document.querySelector(`[data-testid="smb-el-${id}"]`);
        el?.dispatchEvent(
          new PointerEvent('pointerdown', {
            bubbles: true,
            cancelable: true,
            pointerId: 1,
            pointerType: 'mouse',
            button: 0,
          }),
        );
        el?.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, view: window }));
      }, headlineId);
      await page.waitForTimeout(200);
      await page.evaluate((id) => {
        const handle = document.querySelector(`[data-testid="smb-el-resize-${id}"]`);
        if (!handle) throw new Error('missing resize handle');
        const rect = handle.getBoundingClientRect();
        const x0 = rect.left + 4;
        const y0 = rect.top + 4;
        handle.dispatchEvent(
          new PointerEvent('pointerdown', {
            bubbles: true,
            cancelable: true,
            pointerId: 1,
            pointerType: 'mouse',
            button: 0,
            clientX: x0,
            clientY: y0,
          }),
        );
        window.dispatchEvent(
          new PointerEvent('pointermove', {
            bubbles: true,
            cancelable: true,
            pointerId: 1,
            pointerType: 'mouse',
            button: 0,
            clientX: x0 - 220,
            clientY: y0 + 8,
          }),
        );
        window.dispatchEvent(
          new PointerEvent('pointerup', {
            bubbles: true,
            cancelable: true,
            pointerId: 1,
            pointerType: 'mouse',
            button: 0,
            clientX: x0 - 220,
            clientY: y0 + 8,
          }),
        );
      }, headlineId);
      await page.waitForTimeout(400);
      const after = await headlineMeta(page);
      const crashed = await page.evaluate(() => document.body.textContent?.includes('Application error'));
      const narrower = after && before && after.width < before.width - 8;
      const noScroll =
        after &&
        after.overflowY !== 'auto' &&
        after.overflowY !== 'scroll' &&
        (after.editorOverflowY == null ||
          (after.editorOverflowY !== 'auto' && after.editorOverflowY !== 'scroll'));
      if (!crashed && narrower && noScroll) {
        pass('C', `w ${before.width}→${after.width} h ${before.height}→${after.height}`);
      } else {
        fail(
          'C',
          `crashed=${crashed} narrower=${narrower} noScroll=${noScroll} w ${before?.width}→${after?.width}`,
        );
      }
    } catch (e) {
      fail('C', String(e.message || e));
    }

    // ---- TEST D: fullscreen parity ----
    try {
      const before = await headlineMeta(page);
      const fsBtn = page
        .locator(
          '[data-testid="smb-fullscreen"], [data-testid="smb-fullscreen-zoom"], button[aria-label*="Full"], button[aria-label*="Tam"]',
        )
        .first();
      if (!(await fsBtn.count())) throw new Error('fullscreen control missing');
      await fsBtn.click({ force: true });
      await page.waitForTimeout(800);
      const inside = await headlineMeta(page);
      await fsBtn.click({ force: true });
      await page.waitForTimeout(800);
      const after = await headlineMeta(page);
      const sameInside =
        inside &&
        before &&
        inside.text === before.text &&
        Math.abs(inside.width - before.width) < 2 &&
        Math.abs(inside.height - before.height) < 2 &&
        Math.abs(inside.fontSize - before.fontSize) < 1;
      const sameAfter =
        after &&
        before &&
        after.text === before.text &&
        Math.abs(after.width - before.width) < 2 &&
        Math.abs(after.height - before.height) < 2;
      if (sameInside && sameAfter) {
        pass('D', `text+geometry identical in/out FS`);
      } else {
        fail(
          'D',
          `in=${inside?.text}/${inside?.width}x${inside?.height} out=${after?.text}/${after?.width}x${after?.height} was=${before?.text}/${before?.width}x${before?.height}`,
        );
      }
    } catch (e) {
      fail('D', String(e.message || e));
    }

    // ---- TEST E: refresh restores multiline + geometry ----
    try {
      const snapshot = await headlineMeta(page);
      const saveBtn = page.locator('[data-testid="smb-save"]');
      if (await saveBtn.count()) await saveBtn.click({ force: true });
      await page.waitForTimeout(4000);
      await page.reload({ waitUntil: 'domcontentloaded' });
      await waitReady(page);
      await page.waitForTimeout(3500);
      const restored = await headlineMeta(page);
      const ok =
        restored &&
        snapshot &&
        restored.text === snapshot.text &&
        Math.abs(restored.width - snapshot.width) < 3 &&
        Math.abs(restored.height - snapshot.height) < 3 &&
        restored.text.includes('\n');
      if (ok) pass('E', `restored ${JSON.stringify(restored.text)} ${restored.width}x${restored.height}`);
      else {
        fail(
          'E',
          `snap=${JSON.stringify(snapshot?.text)} ${snapshot?.width}x${snapshot?.height} rest=${JSON.stringify(restored?.text)} ${restored?.width}x${restored?.height}`,
        );
      }
    } catch (e) {
      fail('E', String(e.message || e));
    }

    // ---- TEST F: keys edit text, not the canvas ----
    try {
      headlineId = await openHeadlineEditor(page);
      const before = await headlineMeta(page);
      const editor = page.locator(`[data-testid="smb-el-editor-${headlineId}"]`);
      await editor.click();
      await page.keyboard.press('End');
      await page.keyboard.press('ArrowLeft');
      await page.keyboard.press('ArrowRight');
      await page.keyboard.press('Backspace');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(200);
      const mid = await headlineMeta(page);
      const stillEditing = mid?.editing === true;
      const stillThere = mid?.id === headlineId;
      const addedLine = (mid?.text || '').split('\n').length >= (before?.text || '').split('\n').length;
      await page.keyboard.press('Escape');
      await page.waitForTimeout(250);
      const after = await headlineMeta(page);
      const exited = after?.editing === false;
      if (stillEditing && stillThere && addedLine && exited) {
        pass('F', 'backspace/arrows/enter stay in editor; Escape exits');
      } else {
        fail('F', `editing=${stillEditing} there=${stillThere} line=${addedLine} exited=${exited}`);
      }
    } catch (e) {
      fail('F', String(e.message || e));
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((r) => !r.ok);
  console.log('\nSUMMARY', JSON.stringify(results, null, 2));
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
