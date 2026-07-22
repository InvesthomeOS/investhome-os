import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const outDir = path.join(__dirname, '..', 'artifacts', 'ai-g7');
await mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.on('pageerror', (e) => console.log('PAGEERROR', e.message));
page.on('console', (m) => {
  if (m.type() === 'error') console.log('CONSOLE', m.text().slice(0, 200));
});

await page.goto('http://localhost:3000/login', { waitUntil: 'domcontentloaded' });
await page.locator('input[type="email"]').first().fill('superadmin@investhome.demo');
await page.locator('input[type="password"]').first().fill('Demo123!');
await page.locator('button[type="submit"]').first().click();
await page.waitForURL(/dashboard/, { timeout: 45_000 });
await page.goto('http://localhost:3000/dashboard/ai', { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="ai-g7-nav-command_center"]', { timeout: 45_000 });
await page
  .waitForFunction(() => !document.body.innerText.toLowerCase().includes('loading ai workspace'), {
    timeout: 45_000,
  })
  .catch(() => console.log('STILL_LOADING_AFTER_TIMEOUT'));
console.log('URL', page.url());
console.log('HAS_WS', await page.locator('[data-testid="ai-g7-workspace"]').count());
console.log('HAS_NAV', await page.locator('[data-testid="ai-g7-nav-command_center"]').count());
console.log('HAS_KPI', await page.locator('[data-testid="ai-g7-kpi-priorities"]').count());
console.log('BODY_SNIP', (await page.innerText('body')).slice(0, 1500));
await page.screenshot({ path: path.join(outDir, 'debug-ai.png'), fullPage: false });
await browser.close();
