import { chromium } from 'playwright';
import { mkdir, stat, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const outDir = path.join(repoRoot, 'artifacts', 'marketing-g6');
await mkdir(outDir, { recursive: true });

const REQUIRED = [
  '01-overview.png',
  '02-campaigns.png',
  '03-campaign-drawer.png',
  '04-attribution.png',
  '05-funnel.png',
  '06-lead-sources.png',
  '07-website-analytics.png',
  '08-seo.png',
  '09-content-studio.png',
  '10-blog.png',
  '11-social.png',
  '12-email.png',
  '13-paid-ads.png',
  '14-landing-pages.png',
  '15-calculators.png',
  '16-calendar.png',
  '17-ai-insights.png',
  '18-tablet.png',
  '19-turkish.png',
  '20-english.png',
];

console.log('outDir=', outDir);

const base = process.env.BASE_URL || 'http://localhost:3000';
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

async function login() {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
      await page.waitForTimeout(1000);
      await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
      await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
      await page.locator('button[type="submit"]').first().click();
      await page.waitForURL(/dashboard/, { timeout: 60_000 });
      await page.waitForTimeout(1200);
      return;
    } catch (err) {
      console.log('login attempt', attempt, 'failed', err.message);
      if (attempt === 3) throw err;
      await page.waitForTimeout(2000);
    }
  }
}

async function ready(testId) {
  await page.waitForSelector('[data-testid="mkt-g6-workspace"]', { timeout: 60_000 });
  await page.waitForFunction(() => !document.querySelector('[data-testid="mkt-g6-loading"]'), null, {
    timeout: 60_000,
  });
  if (testId) {
    await page.waitForSelector(`[data-testid="${testId}"]`, { timeout: 45_000 });
  }
  await page.waitForTimeout(900);
}

async function clickNav(viewId) {
  await page.getByTestId(`mkt-g6-nav-${viewId}`).click();
  await page.waitForTimeout(500);
}

async function shot(name, testId) {
  await ready(testId);
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: false });
  const size = (await stat(file)).size;
  console.log('saved', file, size);
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

await login();
await page.goto(`${base}/dashboard/marketing`, { waitUntil: 'domcontentloaded', timeout: 60_000 });
await shot('01-overview.png', 'mkt-g6-overview');

await clickNav('campaigns');
await shot('02-campaigns.png', 'mkt-g6-campaigns');

await ready('mkt-g6-campaigns');
const row = page.locator('[data-testid^="mkt-g6-campaign-row-"], [data-testid^="mkt-g6-campaign-card-"]').first();
await row.waitFor({ timeout: 30_000 });
await row.click();
await page.waitForSelector('[data-testid="mkt-g6-drawer"]', { timeout: 15_000 });
await page.waitForTimeout(800);
await shot('03-campaign-drawer.png', 'mkt-g6-drawer');
await page.getByTestId('mkt-g6-drawer-close').click();

const views = [
  ['04-attribution.png', 'attribution', 'mkt-g6-attribution'],
  ['05-funnel.png', 'funnel', 'mkt-g6-funnel'],
  ['06-lead-sources.png', 'lead_sources', 'mkt-g6-lead-sources'],
  ['07-website-analytics.png', 'website_analytics', 'mkt-g6-website-analytics'],
  ['08-seo.png', 'seo', 'mkt-g6-seo'],
  ['09-content-studio.png', 'content_studio', 'mkt-g6-content-studio'],
  ['10-blog.png', 'blog', 'mkt-g6-blog'],
  ['11-social.png', 'social', 'mkt-g6-social'],
  ['12-email.png', 'email', 'mkt-g6-email'],
  ['13-paid-ads.png', 'paid_ads', 'mkt-g6-paid-ads'],
  ['14-landing-pages.png', 'landing_pages', 'mkt-g6-landing-pages'],
  ['15-calculators.png', 'calculators', 'mkt-g6-calculators'],
  ['16-calendar.png', 'calendar', 'mkt-g6-calendar'],
  ['17-ai-insights.png', 'ai_insights', 'mkt-g6-ai-insights'],
];

for (const [name, viewId, testId] of views) {
  await clickNav(viewId);
  await shot(name, testId);
}

await page.setViewportSize({ width: 820, height: 1100 });
await clickNav('overview');
await shot('18-tablet.png', 'mkt-g6-overview');

await page.setViewportSize({ width: 1440, height: 900 });
await page.getByTestId('mkt-g6-lang-tr').click();
await page.waitForTimeout(2500);
await clickNav('overview');
await shot('19-turkish.png', 'mkt-g6-overview');

await page.getByTestId('mkt-g6-lang-en').click();
await page.waitForTimeout(2500);
await clickNav('campaigns');
await shot('20-english.png', 'mkt-g6-campaigns');

await browser.close();

const entries = await readdir(outDir);
const pngs = entries.filter((e) => e.endsWith('.png')).sort();
console.log('\n=== VERIFY LISTING ===');
console.log('dir=', outDir);
let ok = 0;
const sizes = {};
for (const name of REQUIRED) {
  const full = path.join(outDir, name);
  try {
    const s = (await stat(full)).size;
    sizes[name] = s;
    const pass = s > 10_000;
    console.log(`${pass ? 'OK' : 'FAIL'}\t${name}\t${s}`);
    if (pass) ok += 1;
  } catch {
    console.log(`MISSING\t${name}`);
    sizes[name] = 0;
  }
}
await writeFile(path.join(outDir, 'sizes-verified.json'), JSON.stringify({ outDir, ok, total: 20, sizes }, null, 2));
console.log(`\nRESULT ${ok}/20`);
console.log('PNG_COUNT_IN_DIR', pngs.length);
console.log('SIZES_JSON', JSON.stringify(sizes));
if (ok !== 20) process.exitCode = 1;
