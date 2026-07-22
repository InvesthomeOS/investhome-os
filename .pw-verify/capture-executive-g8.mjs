import { chromium } from 'playwright';
import { mkdir, stat, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const outDir = path.join(repoRoot, 'artifacts', 'executive-g8');
await mkdir(outDir, { recursive: true });

const REQUIRED = [
  '01-full-desktop.png',
  '02-header-kpi.png',
  '03-priorities.png',
  '04-financial-position.png',
  '05-sales-investor-pipeline.png',
  '06-project-construction.png',
  '07-marketing-performance.png',
  '08-ai-risks.png',
  '09-approval-center.png',
  '10-upcoming-events.png',
  '11-recent-activity.png',
  '12-customization.png',
  '13-ceo-role.png',
  '14-cfo-role.png',
  '15-sales-role.png',
  '16-pm-role.png',
  '17-tablet.png',
  '18-turkish.png',
  '19-english.png',
  '20-partial-data.png',
];

console.log('outDir=', outDir);

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

async function gotoStable(url, { expectG8 = true } = {}) {
  let lastErr;
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45_000 });
      if (expectG8) {
        await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });
      }
      await page.waitForTimeout(800);
      return;
    } catch (err) {
      lastErr = err;
      console.log('retry goto', attempt, url, err?.message || err);
      await page.waitForTimeout(2000 * attempt);
    }
  }
  throw lastErr;
}

async function login() {
  await gotoStable(`${base}/login`, { expectG8: false });
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
  await page.waitForTimeout(1000);
}

async function waitG8() {
  await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });
  await page.waitForTimeout(1200);
}

async function shot(name, opts = {}) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: Boolean(opts.fullPage) });
  const size = (await stat(file)).size;
  console.log('saved', file, size);
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

async function scrollTo(testId) {
  const el = page.locator(`[data-testid="${testId}"]`).first();
  if (await el.count()) {
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
  }
}

async function setPersona(persona) {
  const panel = page.locator('[data-testid="g8-customize-panel"]');
  if (!(await panel.isVisible().catch(() => false))) {
    await page.locator('[data-testid="g8-customize-toggle"]').click();
    await page.waitForTimeout(400);
  }
  const select = page.locator('[data-testid="g8-persona-select"]');
  await select.waitFor({ timeout: 10_000 });
  await select.selectOption(persona);
  await page.waitForTimeout(600);
}

await login();
await gotoStable(`${base}/dashboard/executive`);
await waitG8();

await shot('01-full-desktop.png', { fullPage: true });

await scrollTo('g8-header');
await shot('02-header-kpi.png');

await scrollTo('g8-section-priorities');
await shot('03-priorities.png');

await scrollTo('g8-section-finance');
await shot('04-financial-position.png');

await scrollTo('g8-section-pipeline');
await shot('05-sales-investor-pipeline.png');

await scrollTo('g8-section-projects');
await shot('06-project-construction.png');

await scrollTo('g8-section-marketing');
await shot('07-marketing-performance.png');

await scrollTo('g8-section-ai');
await shot('08-ai-risks.png');

await scrollTo('g8-section-approvals');
await shot('09-approval-center.png');

await scrollTo('g8-section-upcoming');
await shot('10-upcoming-events.png');

await scrollTo('g8-section-activity');
await shot('11-recent-activity.png');

await setPersona('ceo');
await scrollTo('g8-customize-panel');
await shot('12-customization.png');

await setPersona('ceo');
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(400);
await shot('13-ceo-role.png');

await setPersona('cfo');
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(400);
await shot('14-cfo-role.png');

await setPersona('sales');
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(400);
await shot('15-sales-role.png');

await setPersona('pm');
await page.evaluate(() => window.scrollTo(0, 0));
await page.waitForTimeout(400);
await shot('16-pm-role.png');

await page.setViewportSize({ width: 820, height: 1100 });
await gotoStable(`${base}/dashboard/executive`);
await waitG8();
await shot('17-tablet.png', { fullPage: true });

await page.setViewportSize({ width: 1440, height: 900 });
await gotoStable(`${base}/dashboard/executive`);
await waitG8();
await shot('18-turkish.png', { fullPage: true });

// Switch language to English
const langControl = page.getByRole('button', { name: /Türkçe|English|DİL|Language/i }).first();
if (await langControl.isVisible().catch(() => false)) {
  await langControl.click();
  await page.waitForTimeout(400);
  const enOption = page.getByRole('button', { name: /^English$/i }).or(page.getByText(/^English$/i)).first();
  if (await enOption.isVisible().catch(() => false)) {
    await enOption.click();
    await page.waitForTimeout(1000);
  }
}
await gotoStable(`${base}/dashboard/executive`);
await waitG8();
await shot('19-english.png', { fullPage: true });

await gotoStable(`${base}/dashboard/executive?partial=1`);
await waitG8();
await scrollTo('g8-section-priorities');
await shot('20-partial-data.png');

const files = await readdir(outDir);
const sizes = {};
for (const name of REQUIRED) {
  if (!files.includes(name)) throw new Error(`Missing ${name}`);
  const size = (await stat(path.join(outDir, name))).size;
  sizes[name] = size;
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

await writeFile(
  path.join(outDir, 'sizes-verified.json'),
  JSON.stringify({ verifiedAt: new Date().toISOString(), outDir, sizes }, null, 2),
  'utf8',
);

await browser.close();
console.log('CAPTURE_OK', Object.keys(sizes).length);
