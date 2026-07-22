/**
 * UXR1 V2 Phase 2A — visual capture + route smoke.
 * Run from repo: node artifacts/uxr1-v2-phase2a/capture-screenshots.mjs
 */
import { createRequire } from 'node:module';
import { mkdir, readdir, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(__dirname, '../..');
const OUT = __dirname;

function loadPlaywright() {
  const require = createRequire(import.meta.url);
  const candidates = [
    path.join(REPO, '.pw-verify/node_modules/playwright'),
    path.join(REPO, 'apps/web/node_modules/playwright'),
    path.join(REPO, 'node_modules/playwright'),
  ];
  for (const c of candidates) {
    try {
      return require(c);
    } catch {
      /* continue */
    }
  }
  throw new Error('playwright not found');
}

const { chromium } = loadPlaywright();
await mkdir(OUT, { recursive: true });

const REQUIRED = [
  '01-dashboard-home-desktop.png',
  '02-dashboard-home-shell.png',
  '03-executive-g8-desktop.png',
  '04-executive-g8-kpi.png',
  '05-executive-g8-tablet.png',
  '06-legacy-leads-no-v2.png',
  '07-legacy-investors-spot.png',
  '08-legacy-marketing-spot.png',
  '09-executive-turkish.png',
  '10-executive-english.png',
];

const base = process.env.BASE_URL || 'http://localhost:3000';
console.log('outDir=', OUT);
console.log('base=', base);

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();

async function login() {
  await page.goto(`${base}/login`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.locator('input[type="email"], input[name="email"]').first().fill('superadmin@investhome.demo');
  await page.locator('input[type="password"], input[name="password"]').first().fill('Demo123!');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL(/dashboard/, { timeout: 45_000 });
  await page.waitForTimeout(800);
}

async function shot(name, opts = {}) {
  const file = path.join(OUT, name);
  await page.screenshot({ path: file, fullPage: Boolean(opts.fullPage) });
  const size = (await stat(file)).size;
  console.log('saved', name, size);
  if (size < 10_000) throw new Error(`${name} too small: ${size}`);
}

async function assertV2Shell(expectV2) {
  const v2 = await page.locator('[data-testid="os-shell-v2"]').count();
  const legacy = await page.locator('[data-testid="os-shell"]').count();
  if (expectV2) {
    if (v2 < 1) throw new Error('expected os-shell-v2');
    const attr = await page.locator('[data-ds-version="v2"]').count();
    if (attr < 1) throw new Error('expected data-ds-version=v2');
  } else if (v2 > 0) {
    throw new Error('unexpected os-shell-v2 on legacy route');
  } else if (legacy < 1) {
    throw new Error('expected os-shell on legacy route');
  }
}

const results = { ok: true, routes: [], warnings: [] };

try {
  await login();

  // 1–2 Dashboard home V2
  await page.goto(`${base}/dashboard`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.waitForSelector('[data-testid="dashboard-home-v2"]', { timeout: 60_000 });
  await assertV2Shell(true);
  results.routes.push({ route: '/dashboard', v2: true, status: 'ok' });
  await shot('01-dashboard-home-desktop.png', { fullPage: true });
  await shot('02-dashboard-home-shell.png');

  // 3–4 Executive G8 V2
  await page.goto(`${base}/dashboard/executive`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });
  await assertV2Shell(true);
  results.routes.push({ route: '/dashboard/executive', v2: true, status: 'ok' });
  await shot('03-executive-g8-desktop.png', { fullPage: true });
  const kpi = page.locator('[data-testid="g8-kpi-strip"]').first();
  if (await kpi.count()) {
    await kpi.scrollIntoViewIfNeeded();
    await page.waitForTimeout(400);
  }
  await shot('04-executive-g8-kpi.png');

  // 5 Tablet
  await page.setViewportSize({ width: 1024, height: 900 });
  await page.goto(`${base}/dashboard/executive`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 2,
  );
  if (overflow) {
    results.warnings.push('tablet horizontal overflow detected');
    results.ok = false;
  }
  await shot('05-executive-g8-tablet.png');
  await page.setViewportSize({ width: 1440, height: 900 });

  // 6–8 Legacy spot checks (no V2 shell)
  for (const [route, file, label] of [
    ['/dashboard/leads', '06-legacy-leads-no-v2.png', 'leads'],
    ['/dashboard/investors', '07-legacy-investors-spot.png', 'investors'],
    ['/dashboard/marketing', '08-legacy-marketing-spot.png', 'marketing'],
  ]) {
    const res = await page.goto(`${base}${route}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    const status = res?.status() ?? 0;
    await page.waitForTimeout(1200);
    try {
      await assertV2Shell(false);
      results.routes.push({ route, v2: false, status: status, label, shell: 'legacy' });
    } catch (err) {
      results.ok = false;
      results.warnings.push(`${route}: ${err.message}`);
      results.routes.push({ route, v2: 'error', status, label, error: String(err.message) });
    }
    await shot(file);
  }

  // 9–10 TR / EN via cookie if language selector exists
  await page.goto(`${base}/dashboard/executive`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
  await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });

  async function trySetLocale(locale) {
    // Prefer cookie used by next-intl
    await context.addCookies([
      { name: 'NEXT_LOCALE', value: locale, url: base },
      { name: 'locale', value: locale, url: base },
    ]);
    await page.goto(`${base}/dashboard/executive`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
    await page.waitForSelector('[data-testid="executive-dashboard-g8"]', { timeout: 60_000 });
    await page.waitForTimeout(600);
  }

  await trySetLocale('tr');
  await shot('09-executive-turkish.png', { fullPage: true });
  await trySetLocale('en');
  await shot('10-executive-english.png', { fullPage: true });

  // Verify all required PNGs
  const listing = [];
  for (const name of REQUIRED) {
    const file = path.join(OUT, name);
    const size = (await stat(file)).size;
    listing.push({ name, size, ok: size > 10_000 });
    if (size <= 10_000) {
      results.ok = false;
      results.warnings.push(`${name} size ${size} <= 10KB`);
    }
  }
  await writeFile(path.join(OUT, 'screenshot-dir-listing.txt'), listing.map((r) => `${r.name}\t${r.size}`).join('\n') + '\n');
  await writeFile(path.join(OUT, 'capture-results.json'), JSON.stringify(results, null, 2));

  console.log('capture-results', JSON.stringify(results, null, 2));
  if (!results.ok) process.exitCode = 1;
} finally {
  await browser.close();
}
