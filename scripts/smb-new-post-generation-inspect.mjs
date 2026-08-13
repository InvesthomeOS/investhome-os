/**
 * Visual inspect of SMB generated canvas after live Tests A/B.
 * Does not print secrets. Run: node scripts/smb-new-post-generation-inspect.mjs
 */
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdirSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
const { chromium } = require(join(__dirname, '..', '.pw-verify', 'node_modules', 'playwright'));

const BASE = process.env.SMB_BASE_URL || 'http://localhost:3000';
const EMAIL = process.env.SMB_EMAIL || 'superadmin@investhome.demo';
const PASSWORD = process.env.SMB_PASSWORD || 'Investhome2026!';
const SMB_PATH = '/workspaces/creative-studio/social-media-builder';
const TEMPLE_ID = 'd50708cb-60b3-465a-8b16-6d30f802af8d';
const OUT = join(__dirname, '..', '.pw-verify', 'smb-new-post-inspect');

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
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
    await page.waitForSelector('[data-testid="smb-workspace"]', { timeout: 90000 });
    const projectSelect = page.locator('#smb-project');
    if (await projectSelect.count()) {
      await projectSelect.selectOption(TEMPLE_ID);
      await page.waitForTimeout(2500);
    }
    await page.waitForSelector('[data-testid="smb-artboard"]', { timeout: 30000 });
    await page.waitForFunction(
      () => {
        const img = document.querySelector('[data-testid="smb-artboard-img"]');
        const text = [...document.querySelectorAll('[data-testid^="smb-el-"]')]
          .map((n) => (n.textContent || '').trim())
          .filter(Boolean)
          .join(' ');
        const placeholder = /New social post/i.test(document.body?.innerText || '');
        const unavailable = /Görsel kullanılamıyor/i.test(document.body?.innerText || '');
        return Boolean(img && img.complete && img.naturalWidth > 40 && text.length > 8 && !placeholder && !unavailable);
      },
      null,
      { timeout: 45000 },
    );
    const board = await page.evaluate(() => {
      const art = document.querySelector('[data-testid="smb-artboard"]');
      const img = document.querySelector('[data-testid="smb-artboard-img"]');
      const els = [...document.querySelectorAll('[data-testid^="smb-el-"]')].map((n) => ({
        testid: n.getAttribute('data-testid'),
        text: (n.textContent || '').trim().slice(0, 80),
      }));
      return {
        state: art?.getAttribute('data-image-state') || '',
        cover: art?.getAttribute('data-cover-asset-id') || '',
        selected: art?.getAttribute('data-selected-post-id') || '',
        lifecycle: art?.getAttribute('data-generation-lifecycle') || '',
        imgW: img?.naturalWidth || 0,
        imgH: img?.naturalHeight || 0,
        els,
        placeholder: /New social post/i.test(document.body?.innerText || ''),
        unavailable: /Görsel kullanılamıyor/i.test(document.body?.innerText || ''),
      };
    });
    console.log(JSON.stringify(board, null, 2));
    await page.locator('[data-testid="smb-artboard"]').screenshot({
      path: join(OUT, 'artboard.png'),
    });
    await page.screenshot({ path: join(OUT, 'workspace.png'), fullPage: false });
    if (
      board.state !== 'ready' ||
      !board.cover ||
      board.imgW < 40 ||
      board.placeholder ||
      board.unavailable ||
      board.els.length < 2
    ) {
      throw new Error(`visual inspect failed: ${JSON.stringify(board)}`);
    }
    console.log('VISUAL PASS', join(OUT, 'artboard.png'));
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(String(err?.message || err));
  process.exit(1);
});
