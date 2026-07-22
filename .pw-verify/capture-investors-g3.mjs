import { chromium } from 'playwright';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';

const outDir = path.resolve('../artifacts/investors-g3');
await mkdir(outDir, { recursive: true });

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

async function login() {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  const email = page.locator('input[type="email"], input[name="email"]').first();
  const password = page.locator('input[type="password"], input[name="password"]').first();
  await email.fill('superadmin@investhome.demo');
  await password.fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
  await page.waitForTimeout(1200);
}

async function shot(name, url, setup) {
  if (url) await page.goto(url, { waitUntil: 'domcontentloaded' });
  if (setup) await setup();
  await page.waitForSelector('[data-testid="inv-g3-workspace"]', { timeout: 45_000 });
  // Wait until loading settles (board, list, or panel)
  await page
    .waitForFunction(
      () => {
        const loading = document.body.innerText.includes('yükleniyor') || document.body.innerText.includes('Loading');
        const board = document.querySelector('[data-testid="inv-g3-board"]');
        const list = document.querySelector('[data-testid="inv-g3-list"]');
        const panel = document.querySelector('.inv-g3__panel, [data-testid="inv-g3-analytics"]');
        return !loading && Boolean(board || list || panel);
      },
      { timeout: 45_000 },
    )
    .catch(() => {});
  await page.waitForTimeout(1200);
  await page.screenshot({ path: path.join(outDir, name), fullPage: false });
  console.log('saved', name);
}

await login();

await shot('01-pipeline-desktop.png', `${base}/dashboard/investors`);
await shot('02-list-desktop.png', `${base}/dashboard/investors?view=list`);
await shot('03-drawer-open.png', `${base}/dashboard/investors`, async () => {
  const card = page.locator('[data-testid^="inv-g3-card-"]').first();
  await card.waitFor({ timeout: 30_000 });
  await card.click();
  await page.waitForSelector('[data-testid="inv-g3-drawer"]', { timeout: 15_000 });
});
await shot('04-reservations.png', `${base}/dashboard/investors?view=reservations`);
await shot('05-payments.png', `${base}/dashboard/investors?view=payments`);
await shot('06-portfolio.png', `${base}/dashboard/investors?view=portfolio`);
await shot('07-analytics.png', `${base}/dashboard/investors?view=analytics`);

await page.setViewportSize({ width: 820, height: 1100 });
await shot('08-tablet.png', `${base}/dashboard/investors`);

await page.setViewportSize({ width: 1440, height: 900 });
await shot('09-turkish.png', `${base}/dashboard/investors`);

await page.goto(`${base}/dashboard/investors?view=list`, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('[data-testid="inv-g3-workspace"]', { timeout: 45_000 });
const enBtn = page.getByRole('button', { name: /English/i }).first();
if (await enBtn.isVisible().catch(() => false)) {
  await enBtn.click();
  await page.waitForTimeout(800);
}
await page.screenshot({ path: path.join(outDir, '10-english.png'), fullPage: false });
console.log('saved', '10-english.png');

await browser.close();
console.log('done');
